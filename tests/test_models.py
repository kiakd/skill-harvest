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
