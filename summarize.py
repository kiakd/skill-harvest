# summarize.py
"""Turn a Transcript into a validated Card via an LLM. LLM injected as `complete`."""
import json
import re

import config
from models import Card

_REQUIRED_KEYS = ["category", "summary", "tags", "tools", "steps", "tips", "glossary"]


def _category_block():
    lines = [f'  - "{c["id"]}": {c["label"]}' for c in config.CATEGORIES]
    return "\n".join(lines)


def _extract_json(text):
    """Pull the first JSON object out of an LLM response (handles ```json fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
    if candidate is None:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(candidate)


def _render_transcript(transcript):
    """Render transcript for the LLM, prefixing each line with its timestamp
    (e.g. "[42s] ...") so the model can fill step `t_sec` for jump links.
    Falls back to plain text when there are no timestamped segments."""
    if transcript.segments:
        return "\n".join(f"[{s.t_sec}s] {s.text}" for s in transcript.segments)
    return transcript.text


def _chunk_text(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]


def _map_reduce_text(text, complete):
    """Condense a long transcript into one shorter text via map-reduce."""
    chunks = _chunk_text(text, config.SUMMARIZE_CHUNK_CHARS)
    partials = []
    for idx, chunk in enumerate(chunks):
        prompt = (
            f"นี่คือบางส่วน ({idx + 1}/{len(chunks)}) ของถอดเสียงทูตอเรียล "
            f"สรุปประเด็นที่เอาไปใช้ทำได้จริง (เครื่องมือ/ขั้นตอน/ทริค) เป็นภาษาไทยสั้นๆ:\n\n{chunk}"
        )
        partials.append(complete(prompt))
    return "\n\n".join(partials)


def _build_card_prompt(meta, transcript_text, transcript_source):
    return (
        "คุณเป็นผู้ช่วยสรุปทูตอเรียลให้เป็น 'การ์ดความรู้' ภาษาไทย\n"
        "เน้นความรู้ที่เอาไปใช้ทำได้จริง ไม่ใช่แค่ย่อความ\n\n"
        f"ชื่อคลิป: {meta.title}\nช่อง: {meta.channel}\n\n"
        "เลือก category ให้ตรงที่สุด 1 อันจาก id ต่อไปนี้เท่านั้น "
        "(ถ้าไม่เข้าอันไหนเลยให้ใช้ \"other\"):\n"
        f"{_category_block()}\n\n"
        "ตอบเป็น JSON อย่างเดียว ตาม schema นี้ (ห้ามมีข้อความอื่น):\n"
        "{\n"
        '  "category": "<id จาก list ข้างบน>",\n'
        '  "summary": "<สรุปสั้นๆ>",\n'
        '  "tags": ["<tag ย่อย>"],\n'
        '  "tools": ["<เครื่องมือ>"],\n'
        '  "steps": [{"text": "<ขั้นตอน>", "t_sec": <วินาทีจาก [Ns] ของบรรทัดที่เกี่ยว ใส่เป็นตัวเลข>}],\n'
        '  "tips": ["<ทริค>"],\n'
        '  "glossary": [{"term": "<ศัพท์>", "meaning": "<ความหมาย>"}],\n'
        '  "visual_gap": <true ถ้าบางขั้นตอนน่าจะเป็นภาพล้วน>\n'
        "}\n\n"
        "หมายเหตุ: แต่ละบรรทัดของถอดเสียงขึ้นต้นด้วย [วินาทีs] "
        "ให้ใส่ t_sec ของแต่ละ step เป็นวินาทีของบรรทัดที่ตรงกับขั้นตอนนั้น\n\n"
        f"ถอดเสียง (ที่มา: {transcript_source}):\n{transcript_text}"
    )


def summarize(meta, transcript, harvested_at, manual_category=None,
              complete=None, max_retries=2):
    """Build a validated Card. `complete(prompt)->str` is the LLM call."""
    if complete is None:
        from llm_client import default_complete
        complete = default_complete

    text = _render_transcript(transcript)
    if len(text) > config.SUMMARIZE_CHUNK_CHARS:
        text = _map_reduce_text(text, complete)

    prompt = _build_card_prompt(meta, text, transcript.source)

    data = None
    last_err = None
    for _ in range(max_retries):
        raw = complete(prompt)
        try:
            data = _extract_json(raw)
            missing = [k for k in _REQUIRED_KEYS if k not in data]
            if missing:
                raise ValueError(f"missing keys: {missing}")
            break
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            data = None
    if data is None:
        raise ValueError(f"LLM did not return valid card JSON: {last_err}")

    if manual_category is not None:
        category = manual_category
        category_source = "manual"
    else:
        category = config.normalize_category(data.get("category"))
        category_source = "ai"

    return Card(
        id=f"yt_{meta.video_id}",
        title=meta.title,
        source_url=meta.source_url,
        channel=meta.channel,
        duration_sec=meta.duration_sec,
        category=category,
        category_source=category_source,
        tags=list(data.get("tags", [])),
        harvested_at=harvested_at,
        transcript_source=transcript.source,
        summary=data.get("summary", ""),
        tools=list(data.get("tools", [])),
        steps=list(data.get("steps", [])),
        tips=list(data.get("tips", [])),
        glossary=list(data.get("glossary", [])),
        visual_gap=bool(data.get("visual_gap", False)),
    )
