# summarize.py
"""Turn a Transcript into a validated Card via an LLM.

Flow: resolve the category (manual, or a small AI classification call), then run
a format-specific extraction prompt — tutorial steps (with `detail`) for most
categories, or flashcards for language categories (config.FLASHCARD_CATEGORIES).
The LLM is injected as `complete(prompt)->str`; the classifier as
`classify(meta, text)->str`.
"""
import json
import re

import config
from models import Card

_TUTORIAL_KEYS = ["summary", "tags", "tools", "steps", "tips", "glossary"]
_FLASHCARD_KEYS = ["summary", "tags", "flashcards"]


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
    (e.g. "[42s] ...") so the model can fill step `t_sec` for jump links."""
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
            f"สรุปประเด็นที่เอาไปใช้ทำได้จริงเป็นภาษาไทยสั้นๆ:\n\n{chunk}"
        )
        partials.append(complete(prompt))
    return "\n\n".join(partials)


def _classify_category(meta, text, complete):
    """Ask the LLM to pick one category id from config. Returns a normalized id."""
    prompt = (
        "จัดหมวดทูตอเรียลต่อไปนี้ เลือก id เดียวจาก list (ถ้าไม่เข้าอันไหนใช้ \"other\"):\n"
        f"{_category_block()}\n\n"
        f"ชื่อคลิป: {meta.title}\nช่อง: {meta.channel}\n\n"
        "ตอบเป็น JSON อย่างเดียว: {\"category\": \"<id>\"}\n\n"
        f"เนื้อหา (ตัวอย่าง):\n{text[:2000]}"
    )
    try:
        data = _extract_json(complete(prompt))
        return config.normalize_category(data.get("category"))
    except (ValueError, json.JSONDecodeError):
        return "other"


def _build_tutorial_prompt(meta, transcript_text, transcript_source):
    return (
        "คุณเป็นผู้ช่วยสรุปทูตอเรียลให้เป็น 'การ์ดความรู้' ภาษาไทยที่อ่านแล้วทำตามได้จริง\n\n"
        f"ชื่อคลิป: {meta.title}\nช่อง: {meta.channel}\n\n"
        "ตอบเป็น JSON อย่างเดียว ตาม schema นี้ (ห้ามมีข้อความอื่น):\n"
        "{\n"
        '  "summary": "<สรุปสั้นๆ ว่าคลิปสอนอะไร>",\n'
        '  "tags": ["<tag ย่อย>"],\n'
        '  "tools": ["<เครื่องมือ>"],\n'
        '  "steps": [{"text": "<ขั้นตอนสั้นๆ>", "t_sec": <วินาทีจาก [Ns]>, '
        '"detail": "<อธิบายละเอียดว่าทำยังไง: เมนู/ปุ่มที่กด, ค่าที่ตั้ง, ลำดับ, เหตุผล>"}],\n'
        '  "tips": ["<ทริค>"],\n'
        '  "glossary": [{"term": "<ศัพท์>", "meaning": "<ความหมาย>"}],\n'
        '  "visual_gap": <true ถ้าบางขั้นตอนเป็นภาพล้วน>\n'
        "}\n\n"
        "สำหรับ \"detail\": เขียนสอนคนที่ไม่เคยทำเลยให้ทำตามได้จริง "
        "เติมความรู้ทั่วไปของเครื่องมือได้ถ้าคลิปพูดไม่ละเอียด\n"
        "แต่ละบรรทัดของถอดเสียงขึ้นต้นด้วย [วินาทีs] ใช้เลขนั้นเป็น t_sec ของ step ที่ตรงกัน\n\n"
        f"ถอดเสียง (ที่มา: {transcript_source}):\n{transcript_text}"
    )


def _build_flashcard_prompt(meta, transcript_text, transcript_source):
    return (
        "คุณเป็นผู้ช่วยสร้าง 'flashcard' เรียนภาษาญี่ปุ่นจากคลิปสอน เพื่อใช้ท่องจำ\n\n"
        f"ชื่อคลิป: {meta.title}\nช่อง: {meta.channel}\n\n"
        "ดึงคำศัพท์/คันจิที่คลิปสอน ออกมาเป็น flashcard ตอบเป็น JSON อย่างเดียว:\n"
        "{\n"
        '  "summary": "<สรุปสั้นๆ ว่าคลิปสอนอะไร>",\n'
        '  "tags": ["<tag ย่อย เช่น n5, kanji>"],\n'
        '  "flashcards": [{\n'
        '    "front": "<คำ/คันจิ>",\n'
        '    "reading": "<furigana อ่านยังไง>",\n'
        '    "onyomi": "<ออนโยมิ ถ้าเป็นคันจิ; ละได้>",\n'
        '    "kunyomi": "<คุนโยมิ; ละได้>",\n'
        '    "meaning": "<ความหมายภาษาไทย>",\n'
        '    "example": "<ประโยคตัวอย่าง + คำแปล; ละได้>"\n'
        "  }]\n"
        "}\n\n"
        "เติม furigana/ออน-คุน/ความหมายไทย/ตัวอย่างจากความรู้ของคุณได้ ถ้าคลิปพูดไม่ครบ\n"
        "front, reading, meaning ต้องมีเสมอ; onyomi/kunyomi/example ละได้\n\n"
        f"ถอดเสียง (ที่มา: {transcript_source}):\n{transcript_text}"
    )


def _extract_validated(prompt, complete, required_keys, max_retries):
    """Call the LLM, extract+validate JSON, retry on failure, else raise."""
    last_err = None
    for _ in range(max_retries):
        try:
            data = _extract_json(complete(prompt))
            missing = [k for k in required_keys if k not in data]
            if missing:
                raise ValueError(f"missing keys: {missing}")
            return data
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
    raise ValueError(f"LLM did not return valid card JSON: {last_err}")


def summarize(meta, transcript, harvested_at, manual_category=None,
              complete=None, classify=None, max_retries=2):
    """Build a validated Card. `complete(prompt)->str` is the LLM call;
    `classify(meta, text)->str` resolves the category (defaults to an LLM call)."""
    if complete is None:
        from llm_client import default_complete
        complete = default_complete

    text = _render_transcript(transcript)
    if len(text) > config.SUMMARIZE_CHUNK_CHARS:
        text = _map_reduce_text(text, complete)

    # 1. Resolve category.
    if manual_category is not None:
        category = manual_category
        category_source = "manual"
    else:
        classify = classify or (lambda m, t: _classify_category(m, t, complete))
        category = config.normalize_category(classify(meta, text))
        category_source = "ai"

    # 2. Branch the extraction prompt by kind.
    if config.is_flashcard_category(category):
        kind = "flashcards"
        data = _extract_validated(_build_flashcard_prompt(meta, text, transcript.source),
                                  complete, _FLASHCARD_KEYS, max_retries)
        steps = []
        flashcards = list(data.get("flashcards", []))
    else:
        kind = "tutorial"
        data = _extract_validated(_build_tutorial_prompt(meta, text, transcript.source),
                                  complete, _TUTORIAL_KEYS, max_retries)
        steps = list(data.get("steps", []))
        flashcards = []

    return Card(
        id=f"yt_{meta.video_id}",
        title=meta.title,
        source_url=meta.source_url,
        channel=meta.channel,
        duration_sec=meta.duration_sec,
        category=category,
        category_source=category_source,
        kind=kind,
        tags=list(data.get("tags", [])),
        harvested_at=harvested_at,
        transcript_source=transcript.source,
        summary=data.get("summary", ""),
        tools=list(data.get("tools", [])),
        steps=steps,
        flashcards=flashcards,
        tips=list(data.get("tips", [])),
        glossary=list(data.get("glossary", [])),
        visual_gap=bool(data.get("visual_gap", False)),
    )
