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
