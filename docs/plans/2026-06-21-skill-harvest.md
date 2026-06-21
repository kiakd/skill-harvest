# skill-harvest Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that turns a YouTube link into a structured Thai "knowledge card" (JSON) and a single offline-capable `gallery.html`, with each card assigned one category (AI-guessed, manually overridable).

**Architecture:** A linear pipeline — `fetch` (yt-dlp metadata + caption) → `transcribe` (faster-whisper fallback) → `summarize` (LLM → validated Card with category) → `store` (write `cards/*.json` + regenerate `cards-data.js`). Each stage is a focused module communicating through dataclasses in `models.py`. `gallery.html` is a static template that reads embedded `window.CARDS` so it works from `file://` on mobile with no server.

**Tech Stack:** Python 3.10+, `yt-dlp`, `faster-whisper`, `ffmpeg` (external), OpenAI-compatible LLM endpoint (LM Studio / DeepSeek / OpenRouter) via `requests`, `pytest` for tests.

**Spec:** [docs/specs/2026-06-21-skill-harvest-design.md](../specs/2026-06-21-skill-harvest-design.md)

---

## File Structure

| File | Responsibility |
|---|---|
| `pytest.ini` | Make repo root importable in tests (`pythonpath = .`) |
| `requirements.txt` | Runtime deps |
| `config.py` | Settings (env-driven) + `CATEGORIES` list + category helpers |
| `models.py` | Dataclasses: `Segment`, `VideoMeta`, `Transcript`, `Card` (+ serialization) |
| `fetch.py` | yt-dlp wrapper → `VideoMeta` (+ caption parsing, VTT → segments) |
| `transcribe.py` | Audio download + faster-whisper → `Transcript`, with `cache/` reuse |
| `summarize.py` | LLM client + map-reduce + JSON/schema validation → `Card` (category) |
| `store.py` | Write `cards/<id>.json` + regenerate `cards-data.js` + place `gallery.html` |
| `templates/gallery.html` | Static UI: category chips + tag chips + search + expandable steps |
| `cli.py` | argparse entrypoint, wires the pipeline, `--category` override |
| `tests/test_*.py` | One test module per source module |

Each task below is test-first. Run all commands from the repo root `D:\work_pame\skill-harvest`.

---

## Task 0: Project scaffold

**Files:**
- Create: `pytest.ini`
- Create: `requirements.txt`
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: Create `requirements.txt`**

```text
yt-dlp>=2024.0.0
faster-whisper>=1.0.0
requests>=2.31.0
pytest>=8.0.0
```

- [ ] **Step 3: Create empty `tests/__init__.py`**

```python
```

- [ ] **Step 4: Verify pytest runs (no tests yet)**

Run: `python -m pytest -q`
Expected: exits 0 with "no tests ran".

- [ ] **Step 5: Commit**

```bash
git add pytest.ini requirements.txt tests/__init__.py
git commit -m "chore: project scaffold (pytest, requirements)"
```

---

## Task 1: config.py — settings + categories

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import config


def test_categories_have_required_fields():
    for c in config.CATEGORIES:
        assert "id" in c and "label" in c
        assert c["id"] and c["label"]


def test_other_category_always_present():
    assert "other" in config.category_ids()


def test_normalize_category_keeps_valid_id():
    assert config.normalize_category("pixel-art") == "pixel-art"


def test_normalize_category_falls_back_to_other():
    assert config.normalize_category("nonexistent") == "other"
    assert config.normalize_category(None) == "other"


def test_is_valid_category():
    assert config.is_valid_category("unity") is True
    assert config.is_valid_category("made-up") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 3: Write minimal implementation**

```python
# config.py
"""Central settings + category registry. Settings read from env with defaults."""
import os

# --- LLM (OpenAI-compatible endpoint) ---
LLM_BASE_URL = os.environ.get("SH_LLM_BASE_URL", "http://localhost:1234/v1")
LLM_API_KEY = os.environ.get("SH_LLM_API_KEY", "not-needed")
LLM_MODEL = os.environ.get("SH_LLM_MODEL", "local-model")

# --- Output ---
OUTPUT_LANG = os.environ.get("SH_OUTPUT_LANG", "th")

# --- Folders (relative to repo root) ---
CARDS_DIR = os.environ.get("SH_CARDS_DIR", "cards")
CACHE_DIR = os.environ.get("SH_CACHE_DIR", "cache")
CARDS_DATA_JS = os.environ.get("SH_CARDS_DATA_JS", "cards-data.js")
GALLERY_HTML = os.environ.get("SH_GALLERY_HTML", "gallery.html")

# --- Transcription ---
WHISPER_MODEL_SIZE = os.environ.get("SH_WHISPER_MODEL_SIZE", "medium")

# --- Map-reduce threshold (characters of transcript before chunking) ---
SUMMARIZE_CHUNK_CHARS = int(os.environ.get("SH_SUMMARIZE_CHUNK_CHARS", "8000"))

# --- Caption language preference for yt-dlp ---
CAPTION_LANGS = os.environ.get("SH_CAPTION_LANGS", "th,en").split(",")

# --- Categories: edit here only; AI prompt + gallery both read from this list ---
CATEGORIES = [
    {"id": "pixel-art", "label": "Pixel Art"},
    {"id": "3d", "label": "3D / โมเดล"},
    {"id": "unity", "label": "Unity"},
    {"id": "japanese", "label": "เรียนญี่ปุ่น"},
    {"id": "other", "label": "อื่น ๆ"},  # fallback — must always exist
]


def category_ids():
    """Set of valid category ids."""
    return {c["id"] for c in CATEGORIES}


def is_valid_category(cat_id):
    return cat_id in category_ids()


def normalize_category(cat_id):
    """Return cat_id if valid, else 'other'."""
    return cat_id if cat_id in category_ids() else "other"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): settings + category registry with fallback"
```

---

## Task 2: models.py — data structures

**Files:**
- Create: `models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from models import Segment, VideoMeta, Transcript, Card


def test_segment_roundtrip():
    s = Segment(text="hello", t_sec=42)
    assert s.text == "hello"
    assert s.t_sec == 42


def test_transcript_holds_segments():
    t = Transcript(text="a b", segments=[Segment("a", 0), Segment("b", 5)], source="caption")
    assert t.source == "caption"
    assert len(t.segments) == 2


def test_videometa_defaults():
    m = VideoMeta(video_id="abc", title="T", channel="C", duration_sec=100,
                  source_url="https://youtu.be/abc")
    assert m.chapters == []
    assert m.caption_segments == []
    assert m.caption_text is None


def test_card_to_dict_has_all_schema_keys():
    card = Card(
        id="yt_abc", title="T", source_url="https://youtu.be/abc", channel="C",
        duration_sec=100, category="pixel-art", category_source="ai",
        tags=["aseprite"], harvested_at="2026-06-21", transcript_source="caption",
        summary="s", tools=["Aseprite"], steps=[{"text": "x", "t_sec": 5}],
        tips=["t"], glossary=[{"term": "smear", "meaning": "m"}], visual_gap=False,
    )
    d = card.to_dict()
    for key in ["id", "title", "source_url", "channel", "duration_sec", "category",
                "category_source", "tags", "harvested_at", "transcript_source",
                "summary", "tools", "steps", "tips", "glossary", "visual_gap"]:
        assert key in d
    assert d["category"] == "pixel-art"
    assert d["category_source"] == "ai"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models'`.

- [ ] **Step 3: Write minimal implementation**

```python
# models.py
"""Plain dataclasses passed between pipeline stages."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Segment:
    text: str
    t_sec: int


@dataclass
class VideoMeta:
    video_id: str
    title: str
    channel: str
    duration_sec: int
    source_url: str
    chapters: list = field(default_factory=list)          # [{"title","start_sec"}]
    caption_text: Optional[str] = None                     # joined caption text if any
    caption_segments: list = field(default_factory=list)   # list[Segment]


@dataclass
class Transcript:
    text: str                       # full joined text
    segments: list                  # list[Segment] (may be empty)
    source: str                     # "caption" | "whisper"


@dataclass
class Card:
    id: str
    title: str
    source_url: str
    channel: str
    duration_sec: int
    category: str
    category_source: str            # "ai" | "manual"
    tags: list
    harvested_at: str               # ISO date string
    transcript_source: str          # "caption" | "whisper"
    summary: str
    tools: list
    steps: list                     # [{"text","t_sec"?}]
    tips: list
    glossary: list                  # [{"term","meaning"}]
    visual_gap: bool = False

    def to_dict(self):
        return asdict(self)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat(models): pipeline dataclasses + Card serialization"
```

---

## Task 3: fetch.py — yt-dlp metadata + caption parsing

The heavy network call (`yt-dlp -J`) is injected as a `runner` callable so it can be mocked. VTT parsing is a pure function.

**Files:**
- Create: `fetch.py`
- Test: `tests/test_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch.py
import json
import fetch
from models import VideoMeta


SAMPLE_INFO = {
    "id": "abc123",
    "title": "Smooth Pixel Attack (Aseprite)",
    "channel": "PixelGuru",
    "duration": 754,
    "chapters": [{"title": "Intro", "start_time": 0.0}, {"title": "Smear", "start_time": 90.0}],
    "subtitles": {},
    "automatic_captions": {},
}

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:03.000
ตั้ง keyframe ท่าเริ่ม

00:00:42.500 --> 00:00:45.000
แทรก smear frame
"""


def test_parse_info_builds_videometa():
    m = fetch.parse_info(SAMPLE_INFO, source_url="https://youtu.be/abc123")
    assert isinstance(m, VideoMeta)
    assert m.video_id == "abc123"
    assert m.title.startswith("Smooth Pixel")
    assert m.channel == "PixelGuru"
    assert m.duration_sec == 754
    assert m.chapters == [{"title": "Intro", "start_sec": 0}, {"title": "Smear", "start_sec": 90}]


def test_parse_vtt_extracts_segments():
    segs = fetch.parse_vtt(SAMPLE_VTT)
    assert len(segs) == 2
    assert segs[0].t_sec == 1
    assert segs[0].text == "ตั้ง keyframe ท่าเริ่ม"
    assert segs[1].t_sec == 42  # 42.5 floored


def test_fetch_video_meta_uses_runner(monkeypatch):
    def fake_runner(args):
        # yt-dlp -J ... -> stdout is the info json
        return json.dumps(SAMPLE_INFO)
    m = fetch.fetch_video_meta("https://youtu.be/abc123", runner=fake_runner)
    assert m.video_id == "abc123"
    assert m.caption_text is None  # no captions in sample
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fetch'`.

- [ ] **Step 3: Write minimal implementation**

```python
# fetch.py
"""yt-dlp wrapper -> VideoMeta. Network call injected as `runner` for testability."""
import json
import re
import subprocess

import config
from models import VideoMeta, Segment

_TIMESTAMP_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"
)


def _default_runner(args):
    """Run a command, return stdout as text. Raises on non-zero exit."""
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\n{result.stderr}")
    return result.stdout


def parse_info(info, source_url):
    """Map a yt-dlp info dict -> VideoMeta (without captions)."""
    chapters = []
    for ch in info.get("chapters") or []:
        chapters.append({"title": ch.get("title", ""), "start_sec": int(ch.get("start_time", 0))})
    return VideoMeta(
        video_id=info["id"],
        title=info.get("title", ""),
        channel=info.get("channel") or info.get("uploader", ""),
        duration_sec=int(info.get("duration") or 0),
        source_url=source_url,
        chapters=chapters,
    )


def parse_vtt(vtt_text):
    """Parse WEBVTT text -> list[Segment]. Start time floored to whole seconds."""
    segments = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        m = _TIMESTAMP_RE.search(lines[i])
        if m:
            h, mn, s, _ms = m.group(1), m.group(2), m.group(3), m.group(4)
            t_sec = int(h) * 3600 + int(mn) * 60 + int(s)
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines).strip()
            if text:
                segments.append(Segment(text=text, t_sec=t_sec))
        else:
            i += 1
    return segments


def _pick_caption_lang(info):
    """Return first available caption lang from preference, or None."""
    subs = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    for lang in config.CAPTION_LANGS:
        if lang in subs or lang in auto:
            return lang
    return None


def fetch_video_meta(url, runner=None):
    """Fetch metadata (+ caption text/segments if available) for a YouTube URL."""
    runner = runner or _default_runner
    info = json.loads(runner(["yt-dlp", "-J", "--no-warnings", url]))
    meta = parse_info(info, source_url=url)

    lang = _pick_caption_lang(info)
    if lang:
        # Print the subtitle to stdout as VTT without downloading the video.
        vtt = runner([
            "yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
            "--sub-lang", lang, "--sub-format", "vtt", "-o", "-", url,
        ])
        segs = parse_vtt(vtt)
        if segs:
            meta.caption_segments = segs
            meta.caption_text = " ".join(s.text for s in segs)
    return meta
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fetch.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add fetch.py tests/test_fetch.py
git commit -m "feat(fetch): yt-dlp metadata + VTT caption parsing"
```

---

## Task 4: transcribe.py — Whisper fallback + cache

Caption-first logic lives in `cli`. This module produces a `Transcript`, either from captions (passed in) or by running Whisper. The Whisper model and audio download are injected for testability, and results are cached to `cache/<id>.json`.

**Files:**
- Create: `transcribe.py`
- Test: `tests/test_transcribe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe.py
import json
import transcribe
from models import VideoMeta, Segment, Transcript


def make_meta():
    return VideoMeta(video_id="abc", title="T", channel="C", duration_sec=10,
                     source_url="https://youtu.be/abc")


def test_transcript_from_caption_when_present():
    meta = make_meta()
    meta.caption_text = "hello world"
    meta.caption_segments = [Segment("hello", 0), Segment("world", 2)]
    t = transcribe.get_transcript(meta)
    assert t.source == "caption"
    assert t.text == "hello world"
    assert len(t.segments) == 2


def test_transcript_uses_cache_if_present(tmp_path, monkeypatch):
    monkeypatch.setattr(transcribe.config, "CACHE_DIR", str(tmp_path))
    cache_file = tmp_path / "abc.json"
    cache_file.write_text(json.dumps({
        "text": "cached text",
        "segments": [{"text": "cached text", "t_sec": 3}],
        "source": "whisper",
    }), encoding="utf-8")

    meta = make_meta()  # no caption -> would need whisper, but cache wins
    called = {"whisper": False}

    def fake_whisper(path):
        called["whisper"] = True
        return []

    t = transcribe.get_transcript(meta, whisper_fn=fake_whisper, audio_downloader=lambda u, p: None)
    assert t.text == "cached text"
    assert t.source == "whisper"
    assert called["whisper"] is False  # served from cache


def test_transcript_runs_whisper_and_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(transcribe.config, "CACHE_DIR", str(tmp_path))
    meta = make_meta()

    def fake_whisper(path):
        return [Segment("spoken words", 0)]

    t = transcribe.get_transcript(
        meta, whisper_fn=fake_whisper, audio_downloader=lambda u, p: None
    )
    assert t.source == "whisper"
    assert t.text == "spoken words"
    assert (tmp_path / "abc.json").exists()


def test_whisper_failure_raises_no_silent_card(tmp_path, monkeypatch):
    monkeypatch.setattr(transcribe.config, "CACHE_DIR", str(tmp_path))
    meta = make_meta()

    def boom(path):
        raise RuntimeError("whisper exploded")

    try:
        transcribe.get_transcript(meta, whisper_fn=boom, audio_downloader=lambda u, p: None)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "whisper" in str(e).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_transcribe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'transcribe'`.

- [ ] **Step 3: Write minimal implementation**

```python
# transcribe.py
"""Produce a Transcript: prefer captions, else Whisper. Cache Whisper output."""
import json
import os
import tempfile

import config
from models import Segment, Transcript


def _cache_path(video_id):
    return os.path.join(config.CACHE_DIR, f"{video_id}.json")


def _load_cache(video_id):
    path = _cache_path(video_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    segs = [Segment(text=s["text"], t_sec=s["t_sec"]) for s in data.get("segments", [])]
    return Transcript(text=data["text"], segments=segs, source=data["source"])


def _save_cache(video_id, transcript):
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    payload = {
        "text": transcript.text,
        "segments": [{"text": s.text, "t_sec": s.t_sec} for s in transcript.segments],
        "source": transcript.source,
    }
    with open(_cache_path(video_id), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _default_whisper_fn(audio_path):
    """Transcribe an audio file with faster-whisper -> list[Segment]."""
    from faster_whisper import WhisperModel
    model = WhisperModel(config.WHISPER_MODEL_SIZE)
    segments, _info = model.transcribe(audio_path)
    return [Segment(text=s.text.strip(), t_sec=int(s.start)) for s in segments]


def _default_audio_downloader(url, out_path):
    import subprocess
    result = subprocess.run(
        ["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "mp3",
         "-o", out_path, "--no-warnings", url],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"audio download failed:\n{result.stderr}")


def get_transcript(meta, whisper_fn=None, audio_downloader=None):
    """Return a Transcript for the video. Caption first, cache second, Whisper last."""
    # 1. Captions already fetched?
    if meta.caption_text:
        return Transcript(
            text=meta.caption_text,
            segments=list(meta.caption_segments),
            source="caption",
        )

    # 2. Cached Whisper result?
    cached = _load_cache(meta.video_id)
    if cached is not None:
        return cached

    # 3. Run Whisper.
    whisper_fn = whisper_fn or _default_whisper_fn
    audio_downloader = audio_downloader or _default_audio_downloader

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, f"{meta.video_id}.mp3")
        audio_downloader(meta.source_url, audio_path)
        segments = whisper_fn(audio_path)

    if not segments:
        raise RuntimeError("whisper produced no transcript — refusing to build empty card")

    transcript = Transcript(
        text=" ".join(s.text for s in segments),
        segments=segments,
        source="whisper",
    )
    _save_cache(meta.video_id, transcript)
    return transcript
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_transcribe.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add transcribe.py tests/test_transcribe.py
git commit -m "feat(transcribe): caption-first transcript with whisper fallback + cache"
```

---

## Task 5: summarize.py — LLM → Card with category

The LLM is injected as a `complete(prompt) -> str` callable. This task covers: building the category-aware prompt, map-reduce for long transcripts, JSON parsing, schema validation, and category fallback to `other`.

**Files:**
- Create: `summarize.py`
- Test: `tests/test_summarize.py`

- [ ] **Step 1: Write the failing test**

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


GOOD_JSON = json.dumps({
    "category": "pixel-art",
    "summary": "เทคนิคทำแอนิเมชันโจมตีให้ลื่น",
    "tags": ["aseprite", "smear"],
    "tools": ["Aseprite"],
    "steps": [{"text": "ตั้ง keyframe", "t_sec": 10}],
    "tips": ["อย่าใส่ smear เกิน 2 เฟรม"],
    "glossary": [{"term": "smear frame", "meaning": "เฟรมเบลอ"}],
    "visual_gap": False,
})


def test_summarize_builds_card_from_llm():
    card = summarize.summarize(make_meta(), make_transcript(),
                               harvested_at="2026-06-21",
                               complete=lambda prompt: GOOD_JSON)
    assert card.id == "yt_abc"
    assert card.category == "pixel-art"
    assert card.category_source == "ai"
    assert card.transcript_source == "caption"
    assert card.tags == ["aseprite", "smear"]
    assert card.harvested_at == "2026-06-21"


def test_category_out_of_list_falls_back_to_other():
    bad = json.loads(GOOD_JSON)
    bad["category"] = "totally-made-up"
    card = summarize.summarize(make_meta(), make_transcript(),
                               harvested_at="2026-06-21",
                               complete=lambda prompt: json.dumps(bad))
    assert card.category == "other"
    assert card.category_source == "ai"


def test_manual_category_overrides_llm():
    card = summarize.summarize(make_meta(), make_transcript(),
                               harvested_at="2026-06-21",
                               manual_category="3d",
                               complete=lambda prompt: GOOD_JSON)
    assert card.category == "3d"
    assert card.category_source == "manual"


def test_json_wrapped_in_text_is_extracted():
    noisy = "Sure! Here is the result:\n```json\n" + GOOD_JSON + "\n```\nHope it helps!"
    card = summarize.summarize(make_meta(), make_transcript(),
                               harvested_at="2026-06-21",
                               complete=lambda prompt: noisy)
    assert card.category == "pixel-art"


def test_invalid_json_retries_then_raises():
    calls = {"n": 0}

    def always_bad(prompt):
        calls["n"] += 1
        return "not json at all"

    try:
        summarize.summarize(make_meta(), make_transcript(),
                            harvested_at="2026-06-21", complete=always_bad)
        assert False, "expected ValueError"
    except ValueError:
        pass
    assert calls["n"] >= 2  # retried at least once


def test_long_transcript_triggers_map_reduce(monkeypatch):
    monkeypatch.setattr(summarize.config, "SUMMARIZE_CHUNK_CHARS", 20)
    long_text = "word " * 50  # 250 chars -> multiple chunks
    prompts_seen = []

    def fake_complete(prompt):
        prompts_seen.append(prompt)
        return GOOD_JSON

    summarize.summarize(make_meta(), make_transcript(text=long_text),
                        harvested_at="2026-06-21", complete=fake_complete)
    # map step (>=2 chunks) + reduce step => at least 3 LLM calls
    assert len(prompts_seen) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'summarize'`.

- [ ] **Step 3: Write minimal implementation**

```python
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
        '  "steps": [{"text": "<ขั้นตอน>", "t_sec": <วินาที หรือ ละไว้>}],\n'
        '  "tips": ["<ทริค>"],\n'
        '  "glossary": [{"term": "<ศัพท์>", "meaning": "<ความหมาย>"}],\n'
        '  "visual_gap": <true ถ้าบางขั้นตอนน่าจะเป็นภาพล้วน>\n'
        "}\n\n"
        f"ถอดเสียง (ที่มา: {transcript_source}):\n{transcript_text}"
    )


def summarize(meta, transcript, harvested_at, manual_category=None,
              complete=None, max_retries=2):
    """Build a validated Card. `complete(prompt)->str` is the LLM call."""
    if complete is None:
        from llm_client import default_complete
        complete = default_complete

    text = transcript.text
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add summarize.py tests/test_summarize.py
git commit -m "feat(summarize): LLM->Card with category validation + map-reduce"
```

---

## Task 6: llm_client.py — default OpenAI-compatible completion

A thin real LLM client so `summarize` works end-to-end. No network in tests — we test only request shaping with an injected poster.

**Files:**
- Create: `llm_client.py`
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_client.py
import llm_client


def test_complete_posts_to_endpoint_and_returns_content():
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers

        class Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "hello from llm"}}]}

            def raise_for_status(self):
                pass

        return Resp()

    out = llm_client.complete("say hi", poster=fake_post)
    assert out == "hello from llm"
    assert captured["url"].endswith("/chat/completions")
    assert captured["json"]["messages"][-1]["content"] == "say hi"
    assert "Authorization" in captured["headers"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_llm_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'llm_client'`.

- [ ] **Step 3: Write minimal implementation**

```python
# llm_client.py
"""Minimal OpenAI-compatible chat completion. `poster` injected for tests."""
import config


def _default_poster(url, json, headers, timeout):
    import requests
    return requests.post(url, json=json, headers=headers, timeout=timeout)


def complete(prompt, poster=None, timeout=120):
    """Send a single-user-message chat completion, return the content string."""
    poster = poster or _default_poster
    url = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    resp = poster(url, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# Name used by summarize.py's lazy default import.
default_complete = complete
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_llm_client.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add llm_client.py tests/test_llm_client.py
git commit -m "feat(llm): OpenAI-compatible chat completion client"
```

---

## Task 7: store.py — write card JSON + regenerate cards-data.js

**Files:**
- Create: `store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store.py
import json
import os
import store
from models import Card


def make_card(vid="abc", category="pixel-art"):
    return Card(
        id=f"yt_{vid}", title="T", source_url=f"https://youtu.be/{vid}", channel="C",
        duration_sec=100, category=category, category_source="ai", tags=["aseprite"],
        harvested_at="2026-06-21", transcript_source="caption", summary="s",
        tools=["Aseprite"], steps=[{"text": "x", "t_sec": 5}], tips=["t"],
        glossary=[{"term": "smear", "meaning": "m"}], visual_gap=False,
    )


def _point_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(store.config, "CARDS_DIR", str(tmp_path / "cards"))
    monkeypatch.setattr(store.config, "CARDS_DATA_JS", str(tmp_path / "cards-data.js"))
    monkeypatch.setattr(store.config, "GALLERY_HTML", str(tmp_path / "gallery.html"))


def test_write_card_creates_json(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.write_card(make_card("abc"))
    path = tmp_path / "cards" / "yt_abc.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["category"] == "pixel-art"


def test_regenerate_embeds_all_cards(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.write_card(make_card("abc", "pixel-art"))
    store.write_card(make_card("def", "unity"))
    store.regenerate_cards_data()

    js = (tmp_path / "cards-data.js").read_text(encoding="utf-8")
    assert js.startswith("window.CARDS =")
    # The embedded payload must be valid JSON when the prefix/suffix are stripped.
    payload = js[len("window.CARDS = "):].rstrip().rstrip(";")
    cards = json.loads(payload)
    assert len(cards) == 2
    assert {c["category"] for c in cards} == {"pixel-art", "unity"}


def test_store_card_copies_gallery_template(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.store_card(make_card("abc"))
    assert (tmp_path / "gallery.html").exists()
    assert (tmp_path / "cards-data.js").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'store'`.

- [ ] **Step 3: Write minimal implementation**

```python
# store.py
"""Persist cards as JSON (source of truth) and regenerate gallery data."""
import glob
import json
import os
import shutil

import config

_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates", "gallery.html")


def write_card(card):
    """Write a single card to cards/<id>.json."""
    os.makedirs(config.CARDS_DIR, exist_ok=True)
    path = os.path.join(config.CARDS_DIR, f"{card.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def _load_all_cards():
    cards = []
    for path in sorted(glob.glob(os.path.join(config.CARDS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            cards.append(json.load(f))
    return cards


def regenerate_cards_data():
    """Rebuild cards-data.js (window.CARDS = [...]) from all card JSON files."""
    cards = _load_all_cards()
    payload = json.dumps(cards, ensure_ascii=False, indent=2)
    with open(config.CARDS_DATA_JS, "w", encoding="utf-8") as f:
        f.write(f"window.CARDS = {payload};\n")
    return config.CARDS_DATA_JS


def ensure_gallery():
    """Copy the gallery template next to cards-data.js if not already present."""
    if not os.path.exists(config.GALLERY_HTML):
        shutil.copyfile(_TEMPLATE, config.GALLERY_HTML)
    return config.GALLERY_HTML


def store_card(card):
    """Full store step: write card JSON, regenerate data, ensure gallery exists."""
    write_card(card)
    regenerate_cards_data()
    ensure_gallery()
```

- [ ] **Step 4: Run test to verify it passes**

Note: `store_card` copies `templates/gallery.html`, created in Task 8. Run only the
first two tests now; the third passes after Task 8.

Run: `python -m pytest tests/test_store.py::test_write_card_creates_json tests/test_store.py::test_regenerate_embeds_all_cards -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat(store): write card JSON + regenerate cards-data.js"
```

---

## Task 8: templates/gallery.html — category chips + filters

Static, self-contained HTML. Reads `window.CARDS` from `cards-data.js`. Builds category chips from a derived id set (ordered by `config.CATEGORIES` is not available in JS, so chips are derived from the cards present, with "ทั้งหมด" first). Category filter AND tag filter AND search.

**Files:**
- Create: `templates/gallery.html`
- Test: extends `tests/test_store.py` (smoke) + `tests/test_gallery.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gallery.py
import os

GALLERY = os.path.join(os.path.dirname(__file__), "..", "templates", "gallery.html")


def test_gallery_loads_cards_data_script():
    html = open(GALLERY, encoding="utf-8").read()
    assert '<script src="cards-data.js">' in html or "<script src='cards-data.js'>" in html


def test_gallery_has_category_and_tag_filter_hooks():
    html = open(GALLERY, encoding="utf-8").read()
    assert "window.CARDS" in html
    assert 'id="category-chips"' in html
    assert 'id="tag-chips"' in html
    assert 'id="search"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gallery.py -v`
Expected: FAIL — file `templates/gallery.html` does not exist.

- [ ] **Step 3: Write the template**

Create `templates/gallery.html`:

```html
<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>skill-harvest — คลังความรู้</title>
<style>
  :root { --bg:#0f1115; --card:#1a1e26; --fg:#e6e6e6; --muted:#8a93a6; --accent:#6ad08f; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family:-apple-system,Segoe UI,Roboto,sans-serif; }
  header { position:sticky; top:0; background:var(--bg); padding:12px 14px 6px;
           border-bottom:1px solid #2a2f3a; z-index:10; }
  h1 { font-size:18px; margin:0 0 8px; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; }
  .chip { padding:6px 12px; border-radius:999px; background:var(--card);
          color:var(--fg); border:1px solid #2a2f3a; font-size:13px; cursor:pointer; }
  .chip.active { background:var(--accent); color:#06210f; border-color:var(--accent); }
  #search { width:100%; padding:9px 12px; border-radius:10px; border:1px solid #2a2f3a;
            background:var(--card); color:var(--fg); font-size:14px; margin-top:4px; }
  main { padding:12px 14px 40px; display:grid; gap:12px; }
  .card { background:var(--card); border:1px solid #2a2f3a; border-radius:14px; padding:14px; }
  .card .cat { display:inline-block; font-size:11px; color:var(--accent);
               border:1px solid var(--accent); border-radius:999px; padding:1px 8px; }
  .card h2 { font-size:16px; margin:8px 0 4px; }
  .card .meta { color:var(--muted); font-size:12px; }
  .card .summary { margin:8px 0; font-size:14px; line-height:1.5; }
  .card .tags { display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }
  .card .tag { font-size:11px; color:var(--muted); background:#11151c;
               border-radius:6px; padding:2px 7px; }
  details { margin-top:8px; }
  summary { cursor:pointer; color:var(--accent); font-size:13px; }
  ol { margin:8px 0 0; padding-left:20px; }
  ol li { margin:4px 0; font-size:14px; }
  a.jump { color:var(--accent); text-decoration:none; font-size:12px; }
  .empty { color:var(--muted); text-align:center; padding:40px 0; }
</style>
</head>
<body>
<header>
  <h1>คลังความรู้</h1>
  <div id="category-chips" class="chips"></div>
  <div id="tag-chips" class="chips"></div>
  <input id="search" type="search" placeholder="ค้นหา..." autocomplete="off">
</header>
<main id="cards"></main>

<script src="cards-data.js"></script>
<script>
(function () {
  var CARDS = window.CARDS || [];
  var state = { category: null, tag: null, q: "" };

  function uniq(arr) { return Array.from(new Set(arr)); }

  function fmtTime(s) {
    var m = Math.floor(s / 60), ss = s % 60;
    return m + ":" + (ss < 10 ? "0" : "") + ss;
  }

  function renderChips(el, items, active, onPick, allLabel) {
    el.innerHTML = "";
    var mk = function (label, value) {
      var c = document.createElement("span");
      c.className = "chip" + (active === value ? " active" : "");
      c.textContent = label;
      c.onclick = function () { onPick(active === value ? null : value); };
      el.appendChild(c);
    };
    if (allLabel) mk(allLabel + " (" + CARDS.length + ")", null);
    items.forEach(function (it) { mk(it.label, it.value); });
  }

  function categoryCounts() {
    var counts = {};
    CARDS.forEach(function (c) { counts[c.category] = (counts[c.category] || 0) + 1; });
    return Object.keys(counts).map(function (k) {
      return { value: k, label: k + " (" + counts[k] + ")" };
    });
  }

  function visibleTags() {
    var pool = CARDS.filter(function (c) {
      return !state.category || c.category === state.category;
    });
    return uniq(pool.reduce(function (acc, c) {
      return acc.concat(c.tags || []);
    }, [])).map(function (t) { return { value: t, label: "#" + t }; });
  }

  function matches(c) {
    if (state.category && c.category !== state.category) return false;
    if (state.tag && (c.tags || []).indexOf(state.tag) === -1) return false;
    if (state.q) {
      var hay = (c.title + " " + c.summary + " " + (c.tags || []).join(" ")).toLowerCase();
      if (hay.indexOf(state.q.toLowerCase()) === -1) return false;
    }
    return true;
  }

  function cardHtml(c) {
    var stepsHtml = (c.steps || []).map(function (s) {
      var jump = (typeof s.t_sec === "number")
        ? ' <a class="jump" href="' + c.source_url + '?t=' + s.t_sec + '">@' + fmtTime(s.t_sec) + '</a>'
        : "";
      return "<li>" + escapeHtml(s.text) + jump + "</li>";
    }).join("");
    var tagsHtml = (c.tags || []).map(function (t) {
      return '<span class="tag">#' + escapeHtml(t) + "</span>";
    }).join("");
    var gap = c.visual_gap
      ? '<div class="meta">⚠ บางขั้นตอนอาจเป็นภาพล้วน (รอเฟส 2)</div>' : "";
    return ''
      + '<span class="cat">' + escapeHtml(c.category) + "</span>"
      + "<h2>" + escapeHtml(c.title) + "</h2>"
      + '<div class="meta">' + escapeHtml(c.channel) + " · " + fmtTime(c.duration_sec) + "</div>"
      + '<div class="summary">' + escapeHtml(c.summary) + "</div>"
      + (stepsHtml ? "<details><summary>ขั้นตอน</summary><ol>" + stepsHtml + "</ol></details>" : "")
      + gap
      + '<div class="tags">' + tagsHtml + "</div>";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function render() {
    renderChips(document.getElementById("category-chips"), categoryCounts(),
      state.category, function (v) { state.category = v; state.tag = null; render(); }, "ทั้งหมด");
    renderChips(document.getElementById("tag-chips"), visibleTags(),
      state.tag, function (v) { state.tag = v; render(); }, null);

    var host = document.getElementById("cards");
    var shown = CARDS.filter(matches);
    if (!shown.length) { host.innerHTML = '<div class="empty">ไม่พบการ์ด</div>'; return; }
    host.innerHTML = "";
    shown.forEach(function (c) {
      var el = document.createElement("article");
      el.className = "card";
      el.innerHTML = cardHtml(c);
      host.appendChild(el);
    });
  }

  document.getElementById("search").addEventListener("input", function (e) {
    state.q = e.target.value; render();
  });
  render();
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_gallery.py tests/test_store.py -v`
Expected: PASS (all gallery + all 3 store tests now pass).

- [ ] **Step 5: Commit**

```bash
git add templates/gallery.html tests/test_gallery.py
git commit -m "feat(gallery): static UI with category chips, tag filter, search"
```

---

## Task 9: cli.py — wire the pipeline + --category override

**Files:**
- Create: `cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
import cli


def test_validate_category_accepts_valid():
    assert cli.validate_category("unity") == "unity"


def test_validate_category_rejects_invalid():
    try:
        cli.validate_category("not-a-category")
        assert False, "expected SystemExit"
    except SystemExit as e:
        assert e.code != 0


def test_validate_category_none_passes_through():
    assert cli.validate_category(None) is None


def test_run_pipeline_threads_manual_category(monkeypatch):
    from models import VideoMeta, Transcript, Segment, Card

    meta = VideoMeta(video_id="abc", title="T", channel="C", duration_sec=10,
                     source_url="https://youtu.be/abc")
    transcript = Transcript(text="hi", segments=[Segment("hi", 0)], source="caption")

    seen = {}

    def fake_fetch(url):
        return meta

    def fake_transcript(m):
        return transcript

    def fake_summarize(m, t, harvested_at, manual_category=None):
        seen["manual_category"] = manual_category
        seen["harvested_at"] = harvested_at
        return Card(id="yt_abc", title="T", source_url=m.source_url, channel="C",
                    duration_sec=10, category=manual_category or "other",
                    category_source="manual" if manual_category else "ai", tags=[],
                    harvested_at=harvested_at, transcript_source=t.source, summary="s",
                    tools=[], steps=[], tips=[], glossary=[], visual_gap=False)

    stored = {}

    def fake_store(card):
        stored["card"] = card

    card = cli.run_pipeline(
        "https://youtu.be/abc", manual_category="3d", harvested_at="2026-06-21",
        fetch_fn=fake_fetch, transcript_fn=fake_transcript,
        summarize_fn=fake_summarize, store_fn=fake_store,
    )
    assert seen["manual_category"] == "3d"
    assert seen["harvested_at"] == "2026-06-21"
    assert stored["card"].id == "yt_abc"
    assert card.category == "3d"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cli'`.

- [ ] **Step 3: Write minimal implementation**

```python
# cli.py
"""Entrypoint: harvest a YouTube link into a knowledge card."""
import argparse
import datetime
import sys

import config
import fetch
import transcribe
import summarize as summarize_mod
import store as store_mod


def validate_category(cat_id):
    """Return cat_id if valid or None; exit with error if an unknown id is given."""
    if cat_id is None:
        return None
    if not config.is_valid_category(cat_id):
        valid = ", ".join(sorted(config.category_ids()))
        sys.stderr.write(f"error: ไม่รู้จักหมวด '{cat_id}'. หมวดที่มี: {valid}\n")
        raise SystemExit(2)
    return cat_id


def run_pipeline(url, manual_category, harvested_at,
                 fetch_fn=None, transcript_fn=None, summarize_fn=None, store_fn=None):
    """fetch -> transcript -> summarize -> store. Deps injected for testing."""
    fetch_fn = fetch_fn or fetch.fetch_video_meta
    transcript_fn = transcript_fn or transcribe.get_transcript
    summarize_fn = summarize_fn or summarize_mod.summarize
    store_fn = store_fn or store_mod.store_card

    meta = fetch_fn(url)
    transcript = transcript_fn(meta)
    card = summarize_fn(meta, transcript, harvested_at=harvested_at,
                        manual_category=manual_category)
    store_fn(card)
    return card


def main(argv=None):
    parser = argparse.ArgumentParser(prog="harvest", description="สรุปทูตอเรียล YouTube เป็นการ์ดความรู้")
    parser.add_argument("url", help="ลิงก์ YouTube")
    parser.add_argument("--category", default=None,
                        help="กำหนดหมวดเอง (override AI). ต้องเป็น id ที่มีใน config")
    args = parser.parse_args(argv)

    manual_category = validate_category(args.category)
    harvested_at = datetime.date.today().isoformat()

    card = run_pipeline(args.url, manual_category=manual_category, harvested_at=harvested_at)
    print(f"✓ การ์ด {card.id} [{card.category}] -> {config.CARDS_DIR}/{card.id}.json")
    print(f"  เปิดดูคลัง: {config.GALLERY_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all tests pass (Tasks 1–9).

- [ ] **Step 6: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat(cli): wire pipeline + --category override with validation"
```

---

## Task 10: README + manual smoke test

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# skill-harvest

สรุปทูตอเรียล YouTube เป็น "การ์ดความรู้" ภาษาไทยแบบ interactive เก็บเป็นคลังส่วนตัว

## ติดตั้ง
\`\`\`bash
pip install -r requirements.txt
# ต้องมี ffmpeg ในเครื่อง (สำหรับถอดเสียงคลิปที่ไม่มี caption)
\`\`\`

## ตั้งค่า LLM (OpenAI-compatible)
ตั้ง env ตามปลายทางที่ใช้ (ดีฟอลต์ = LM Studio ในเครื่อง):
\`\`\`bash
export SH_LLM_BASE_URL=http://localhost:1234/v1
export SH_LLM_MODEL=local-model
export SH_LLM_API_KEY=not-needed
\`\`\`

## ใช้งาน
\`\`\`bash
python cli.py "https://youtu.be/<id>"               # AI เดาหมวดให้
python cli.py "https://youtu.be/<id>" --category 3d # กำหนดหมวดเอง
\`\`\`
เปิด `gallery.html` (เปิดไฟล์ตรงๆ บนมือถือได้ ไม่ต้องรันเซิร์ฟเวอร์)

## หมวดหมู่
แก้รายชื่อหมวดที่ `CATEGORIES` ใน `config.py` ที่เดียว — AI และ gallery เห็นพร้อมกัน

## เทสต์
\`\`\`bash
python -m pytest -q
\`\`\`
```

- [ ] **Step 2: Manual smoke test (real network, optional but recommended)**

Ensure an LLM endpoint is running, then:

Run: `python cli.py "https://youtu.be/<a-talky-tutorial-id>"`
Expected: prints `✓ การ์ด yt_<id> [<category>] -> cards/...`, creates `cards/yt_<id>.json`, `cards-data.js`, and `gallery.html`. Open `gallery.html` in a browser — the card appears, category chip filters it, step timestamps link into the video.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, usage, categories"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** pipeline (§3) → Tasks 3–9; file structure (§4) → all tasks; output JSON+gallery (§5) → Tasks 7–8; schema incl. category (§6, §10) → Tasks 2, 5; error handling (§7) → Task 4 (empty transcript), Task 5 (schema retry, category fallback), Task 9 (`--category` validation); testing (§8) → tests in every task; categories (§10) → Tasks 1, 5, 8, 9. Phase-2 items (`frames.py`, vision) are intentionally **out of scope**.
- **Type consistency:** `complete(prompt)->str`, `whisper_fn(path)->list[Segment]`, `audio_downloader(url, path)`, `summarize(meta, transcript, harvested_at, manual_category=None, complete=None)`, `store_card(card)` are used identically across tasks and tests.
- **Determinism:** `harvested_at` is injected (never `date.today()` inside testable code) so summarize/store tests are stable.
