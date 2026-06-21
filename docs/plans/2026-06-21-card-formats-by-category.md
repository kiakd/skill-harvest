# Card Formats by Category — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a card's format depend on its category — tutorial categories produce step-by-step cards with AI-enriched `detail`, while the `japanese` category produces flip flashcards (KIOKU-style) for memorization.

**Architecture:** Add a `kind` field ("tutorial" | "flashcards") to the Card. `summarize` first resolves the category (manual or a small AI classification call), then picks a format-specific extraction prompt. The gallery renders by `kind`: flip cards for flashcards, collapsible step detail for tutorials. Backward compatible — old cards default to tutorial.

**Tech Stack:** Python 3 (existing modules: config, models, summarize, store, cli), static `templates/gallery.html`, pytest. No new dependencies.

**Spec:** [docs/specs/2026-06-21-skill-harvest-design.md](../specs/2026-06-21-skill-harvest-design.md) — section 11.

---

## File Structure

| File | Change |
|---|---|
| `config.py` | Add `FLASHCARD_CATEGORIES` + `is_flashcard_category()` |
| `models.py` | `Card` gains `kind` (default "tutorial") and `flashcards` (default []) |
| `summarize.py` | Resolve category first, branch to tutorial vs flashcard prompt; tutorial steps gain `detail` |
| `templates/gallery.html` | Render by `kind`: flip flashcards + collapsible step detail |
| `README.md` | Note flashcards for the japanese category |
| `tests/test_*.py` | New/updated tests per task |

Run all commands from the repo root `D:\work_pame\skill-harvest`. Tests use `python -m pytest` with `PYTHONPATH=.` (already configured in `pytest.ini`).

---

## Task 1: config — flashcard categories

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_config.py`)

```python
def test_flashcard_categories_subset_of_categories():
    assert config.FLASHCARD_CATEGORIES <= config.category_ids()


def test_is_flashcard_category():
    assert config.is_flashcard_category("japanese") is True
    assert config.is_flashcard_category("pixel-art") is False
    assert config.is_flashcard_category("other") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError: module 'config' has no attribute 'FLASHCARD_CATEGORIES'`.

- [ ] **Step 3: Implement** — add to `config.py` immediately after the `CATEGORIES` list (before `category_ids`)

```python
# Categories whose cards are flashcards (memorization) instead of tutorials.
FLASHCARD_CATEGORIES = {"japanese"}


def is_flashcard_category(cat_id):
    """True if this category produces flip-flashcard cards (vs tutorial steps)."""
    return cat_id in FLASHCARD_CATEGORIES
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (all config tests).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): FLASHCARD_CATEGORIES + is_flashcard_category"
```

---

## Task 2: models — Card gains kind + flashcards

**Files:**
- Modify: `models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_models.py`)

```python
def test_card_defaults_kind_tutorial_and_empty_flashcards():
    card = Card(
        id="yt_x", title="T", source_url="u", channel="C", duration_sec=1,
        category="pixel-art", category_source="ai", tags=[], harvested_at="2026-06-21",
        transcript_source="caption", summary="s", tools=[], steps=[], tips=[],
        glossary=[],
    )
    assert card.kind == "tutorial"
    assert card.flashcards == []
    assert "kind" in card.to_dict()
    assert "flashcards" in card.to_dict()


def test_card_can_hold_flashcards():
    card = Card(
        id="yt_x", title="T", source_url="u", channel="C", duration_sec=1,
        category="japanese", category_source="ai", tags=[], harvested_at="2026-06-21",
        transcript_source="caption", summary="s", tools=[], steps=[], tips=[],
        glossary=[], kind="flashcards",
        flashcards=[{"front": "言葉", "reading": "ことば", "meaning": "คำพูด"}],
    )
    assert card.kind == "flashcards"
    assert card.flashcards[0]["front"] == "言葉"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'kind'`.

- [ ] **Step 3: Implement** — in `models.py`, change the `Card` dataclass tail (the `visual_gap` line) to add the two fields after it:

```python
    visual_gap: bool = False
    kind: str = "tutorial"          # "tutorial" | "flashcards"
    flashcards: list = field(default_factory=list)   # [{front,reading,onyomi?,kunyomi?,meaning,example?}]
```

(`field` is already imported in `models.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat(models): Card gains kind + flashcards fields"
```

---

## Task 3: summarize — resolve category, branch tutorial vs flashcards

This rewrites `summarize.py`. The LLM is injected as `complete(prompt)->str`; the category classifier is injected as `classify(meta, text)->str` (defaults to an LLM call). Tutorial steps now include `detail`.

**Files:**
- Modify: `summarize.py` (full replacement)
- Test: `tests/test_summarize.py` (full replacement)

- [ ] **Step 1: Write the failing tests** — replace the entire contents of `tests/test_summarize.py` with:

```python
# tests/test_summarize.py
import json
import summarize
from models import VideoMeta, Transcript, Segment


def make_meta():
    return VideoMeta(video_id="abc", title="Pixel Attack", channel="PixelGuru",
                     duration_sec=120, source_url="https://youtu.be/abc")


def make_transcript(text="some short transcript", source="caption"):
    return Transcript(text=text, segments=[Segment(text=text, t_sec=10)], source=source)


TUTORIAL_JSON = json.dumps({
    "summary": "เทคนิคทำแอนิเมชันโจมตีให้ลื่น",
    "tags": ["aseprite", "smear"],
    "tools": ["Aseprite"],
    "steps": [{"text": "ตั้ง keyframe", "t_sec": 10, "detail": "เปิด timeline แล้วกด ..."}],
    "tips": ["อย่าใส่ smear เกิน 2 เฟรม"],
    "glossary": [{"term": "smear frame", "meaning": "เฟรมเบลอ"}],
    "visual_gap": False,
})

FLASHCARD_JSON = json.dumps({
    "summary": "คำศัพท์พื้นฐาน JLPT N5",
    "tags": ["n5", "kanji"],
    "flashcards": [
        {"front": "言葉", "reading": "ことば", "onyomi": "ゲン", "kunyomi": "いう",
         "meaning": "คำพูด, ภาษา", "example": "言葉を覚える — จำคำศัพท์"},
    ],
})


def test_tutorial_card_when_category_is_tutorial():
    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               classify=lambda m, t: "pixel-art",
                               complete=lambda prompt: TUTORIAL_JSON)
    assert card.kind == "tutorial"
    assert card.category == "pixel-art"
    assert card.steps[0]["detail"].startswith("เปิด timeline")
    assert card.flashcards == []


def test_flashcard_card_when_category_is_japanese():
    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               classify=lambda m, t: "japanese",
                               complete=lambda prompt: FLASHCARD_JSON)
    assert card.kind == "flashcards"
    assert card.category == "japanese"
    assert card.flashcards[0]["front"] == "言葉"
    assert card.flashcards[0]["meaning"] == "คำพูด, ภาษา"
    assert card.steps == []


def test_manual_japanese_category_uses_flashcards_and_skips_classify():
    called = {"classify": False}

    def classify(m, t):
        called["classify"] = True
        return "pixel-art"

    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               manual_category="japanese", classify=classify,
                               complete=lambda prompt: FLASHCARD_JSON)
    assert card.kind == "flashcards"
    assert card.category == "japanese"
    assert card.category_source == "manual"
    assert called["classify"] is False  # manual category -> no classification call


def test_classify_out_of_list_falls_back_to_other_tutorial():
    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               classify=lambda m, t: "totally-made-up",
                               complete=lambda prompt: TUTORIAL_JSON)
    assert card.category == "other"
    assert card.kind == "tutorial"


def test_tutorial_sends_timestamps_to_llm():
    seen = {}

    def capture(prompt):
        seen["prompt"] = prompt
        return TUTORIAL_JSON

    t = Transcript(text="x", segments=[Segment("block poses", 42), Segment("smear", 132)],
                   source="caption")
    summarize.summarize(make_meta(), t, harvested_at="2026-06-21",
                        classify=lambda m, tx: "pixel-art", complete=capture)
    assert "[42s]" in seen["prompt"] and "[132s]" in seen["prompt"]


def test_invalid_json_retries_then_raises():
    calls = {"n": 0}

    def always_bad(prompt):
        calls["n"] += 1
        return "not json at all"

    try:
        summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                            classify=lambda m, t: "pixel-art", complete=always_bad)
        assert False, "expected ValueError"
    except ValueError:
        pass
    assert calls["n"] >= 2


def test_long_transcript_triggers_map_reduce(monkeypatch):
    monkeypatch.setattr(summarize.config, "SUMMARIZE_CHUNK_CHARS", 20)
    long_text = "word " * 50
    calls = {"n": 0}

    def fake_complete(prompt):
        calls["n"] += 1
        return TUTORIAL_JSON

    summarize.summarize(make_meta(), make_transcript(text=long_text), harvested_at="2026-06-21",
                        classify=lambda m, t: "pixel-art", complete=fake_complete)
    assert calls["n"] >= 3  # several map-chunk calls + the content call


def test_default_classify_uses_complete_when_no_manual_category():
    # When neither manual_category nor classify is given, classification uses `complete`.
    prompts = []

    def complete(prompt):
        prompts.append(prompt)
        # first call is the classification prompt; return a category, then content
        if "จัดหมวด" in prompt:
            return json.dumps({"category": "pixel-art"})
        return TUTORIAL_JSON

    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               complete=complete)
    assert card.category == "pixel-art"
    assert any("จัดหมวด" in p for p in prompts)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: FAIL (current `summarize` has no `classify` param / no `kind`).

- [ ] **Step 3: Implement** — replace the entire contents of `summarize.py` with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: PASS (8 tests). Then run the whole suite: `python -m pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add summarize.py tests/test_summarize.py
git commit -m "feat(summarize): resolve category then branch tutorial vs flashcards"
```

---

## Task 4: gallery — render by kind (flip flashcards + step detail)

**Files:**
- Modify: `templates/gallery.html`
- Test: `tests/test_gallery.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_gallery.py`)

```python
def test_gallery_supports_flashcards_and_step_detail():
    html = open(GALLERY, encoding="utf-8").read()
    # branches on kind, with a default for old cards
    assert 'c.kind' in html
    # flashcard flip support
    assert "flip" in html
    assert "flipped" in html
    # tutorial step detail collapsible
    assert "อธิบายเพิ่ม" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gallery.py -v`
Expected: FAIL (current template has no flip/detail).

- [ ] **Step 3: Implement** — three edits to `templates/gallery.html`.

**(3a)** Add CSS. Find the line:
```css
  .empty { color:var(--muted); text-align:center; padding:40px 0; }
```
and insert BEFORE it:
```css
  ol li details { margin-top:4px; }
  ol li summary { font-size:12px; }
  .flashcards { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; margin-top:8px; }
  .flip { background:transparent; height:120px; cursor:pointer; perspective:800px; }
  .flip-inner { position:relative; width:100%; height:100%; transition:transform .5s; transform-style:preserve-3d; }
  .flip.flipped .flip-inner { transform:rotateY(180deg); }
  .face { position:absolute; width:100%; height:100%; backface-visibility:hidden;
          border:1px solid #2a2f3a; border-radius:10px; padding:8px; overflow:auto;
          display:flex; flex-direction:column; justify-content:center; }
  .face.front { background:#11151c; align-items:center; text-align:center; }
  .face.front .jp { font-size:26px; }
  .face.front .reading { color:var(--muted); font-size:13px; margin-top:4px; }
  .face.back { background:#161b24; transform:rotateY(180deg); font-size:12px; gap:2px; }
  .face.back .mean { color:var(--accent); margin-top:4px; }
  .face.back .ex { color:var(--muted); margin-top:4px; font-size:11px; }
```

**(3b)** Replace the `cardHtml` function body's step rendering and add flashcard rendering. Find:
```javascript
  function cardHtml(c) {
    var stepsHtml = (c.steps || []).map(function (s) {
      var jump = (typeof s.t_sec === "number")
        ? ' <a class="jump" href="' + videoUrlAt(c, s.t_sec) + '" target="_blank" rel="noopener">@' + fmtTime(s.t_sec) + '</a>'
        : "";
      return "<li>" + escapeHtml(s.text) + jump + "</li>";
    }).join("");
```
and replace it with:
```javascript
  function flashcardsHtml(c) {
    var cards = (c.flashcards || []).map(function (f) {
      var backRows = "";
      if (f.onyomi) backRows += "<div>On: " + escapeHtml(f.onyomi) + "</div>";
      if (f.kunyomi) backRows += "<div>Kun: " + escapeHtml(f.kunyomi) + "</div>";
      backRows += '<div class="mean">' + escapeHtml(f.meaning) + "</div>";
      if (f.example) backRows += '<div class="ex">' + escapeHtml(f.example) + "</div>";
      return ''
        + '<div class="flip" onclick="this.classList.toggle(\'flipped\')">'
        + '<div class="flip-inner">'
        + '<div class="face front"><div class="jp">' + escapeHtml(f.front) + "</div>"
        + '<div class="reading">' + escapeHtml(f.reading || "") + "</div></div>"
        + '<div class="face back">' + backRows + "</div>"
        + "</div></div>";
    }).join("");
    return cards ? '<div class="flashcards">' + cards + "</div>" : "";
  }

  function stepsHtmlFor(c) {
    return (c.steps || []).map(function (s) {
      var jump = (typeof s.t_sec === "number")
        ? ' <a class="jump" href="' + videoUrlAt(c, s.t_sec) + '" target="_blank" rel="noopener">@' + fmtTime(s.t_sec) + '</a>'
        : "";
      var detail = s.detail
        ? "<details><summary>อธิบายเพิ่ม</summary><div>" + escapeHtml(s.detail) + "</div></details>"
        : "";
      return "<li>" + escapeHtml(s.text) + jump + detail + "</li>";
    }).join("");
  }

  function cardHtml(c) {
    var kind = c.kind || "tutorial";
    var stepsHtml = stepsHtmlFor(c);
```

**(3c)** Replace the body section that builds the steps `<details>` block. Find:
```javascript
      + (stepsHtml ? "<details><summary>ขั้นตอน</summary><ol>" + stepsHtml + "</ol></details>" : "")
      + gap
```
and replace it with:
```javascript
      + (kind === "flashcards"
          ? flashcardsHtml(c)
          : (stepsHtml ? "<details open><summary>ขั้นตอน</summary><ol>" + stepsHtml + "</ol></details>" : ""))
      + gap
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gallery.py tests/test_store.py -v`
Expected: PASS. Then `python -m pytest -q` — whole suite green.

- [ ] **Step 5: Commit**

```bash
git add templates/gallery.html tests/test_gallery.py
git commit -m "feat(gallery): render flip flashcards + collapsible step detail by kind"
```

---

## Task 5: README note + manual visual check

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update `README.md`** — find the "## หมวดหมู่" section and append after its existing lines:

```markdown

การ์ดปรับรูปแบบตามหมวด: หมวดสอนทำ (pixel-art/3d/unity) = ขั้นตอน + คำอธิบายละเอียด,
หมวด `japanese` = flashcard พลิกหน้า-หลังไว้ท่องจำ
```

- [ ] **Step 2: Manual visual check (no network needed)** — regenerate the gallery from a hand-built flashcard card and a tutorial card, then open it.

Run this from the repo root:
```bash
python -c "import store; from models import Card; \
store.config.CARDS_DIR='cards'; \
store.write_card(Card(id='yt_demoJP', title='JLPT N5 Vocab', source_url='https://youtu.be/demoJP', channel='Sensei', duration_sec=300, category='japanese', category_source='ai', tags=['n5'], harvested_at='2026-06-21', transcript_source='caption', summary='คำศัพท์ N5', tools=[], steps=[], tips=[], glossary=[], kind='flashcards', flashcards=[{'front':'言葉','reading':'ことば','onyomi':'ゲン','kunyomi':'いう','meaning':'คำพูด, ภาษา','example':'言葉を覚える — จำคำศัพท์'}])); \
store.regenerate_cards_data(); store.ensure_gallery(); print('ok')"
```
Open `gallery.html`. Expected: a "เรียนญี่ปุ่น" chip; the japanese card shows a small flip card reading "言葉 / ことば" that flips on tap to show On/Kun/meaning/example. Delete the demo afterward: `rm cards/yt_demoJP.json` then `python -c "import store; store.regenerate_cards_data()"`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: note card formats per category (tutorial vs flashcards)"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** §11.1 format selection → Task 1 (config) + Task 3 (classify+branch); §11.2 tutorial detail → Task 3 (prompt) + Task 4 (collapsible); §11.3 flashcards → Task 2 (model) + Task 3 (prompt) + Task 4 (flip UI); §11.4 backward compat → Task 2 (defaults) + Task 4 (`c.kind || "tutorial"`, detail only if present).
- **Type consistency:** `summarize(meta, transcript, harvested_at, manual_category=None, complete=None, classify=None, max_retries=2)`; `classify(meta, text)->str`; Card fields `kind` (str) and `flashcards` (list of dicts with keys front/reading/onyomi/kunyomi/meaning/example). Gallery reads exactly those keys.
- **cli unchanged:** `run_pipeline` calls `summarize_fn(meta, transcript, harvested_at=, manual_category=)` — the new `classify`/`complete` params default correctly, so cli needs no change.
- **No silent caps:** classification adds one short LLM call only on the AI path (manual category skips it).
