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
        if "จัดหมวด" in prompt:
            return json.dumps({"category": "pixel-art"})
        return TUTORIAL_JSON

    card = summarize.summarize(make_meta(), make_transcript(), harvested_at="2026-06-21",
                               complete=complete)
    assert card.category == "pixel-art"
    assert any("จัดหมวด" in p for p in prompts)
