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
