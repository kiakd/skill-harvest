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


def test_timestamps_are_sent_to_the_llm_for_step_t_sec():
    seen = {}

    def capture(prompt):
        seen["prompt"] = prompt
        return GOOD_JSON

    t = Transcript(text="ignored joined text",
                   segments=[Segment("block the key poses", 42),
                             Segment("add a smear frame", 132)],
                   source="caption")
    summarize.summarize(make_meta(), t, harvested_at="2026-06-21", complete=capture)
    # the model must SEE the seconds, otherwise it can never fill step t_sec
    assert "[42s]" in seen["prompt"]
    assert "[132s]" in seen["prompt"]


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
