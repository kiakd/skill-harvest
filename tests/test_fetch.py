# tests/test_fetch.py
import json
import sys
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


def test_fetch_video_meta_uses_runner():
    def fake_runner(args):
        # yt-dlp -J ... -> stdout is the info json
        return json.dumps(SAMPLE_INFO)
    # inject an empty caption fetcher so the test never touches the network
    m = fetch.fetch_video_meta("https://youtu.be/abc123", runner=fake_runner,
                               caption_fetcher=lambda vid, langs: [])
    assert m.video_id == "abc123"
    assert m.caption_text is None  # no captions in sample


def test_caption_fetcher_is_primary_and_skips_ytdlp():
    from models import Segment
    calls = {"runner": 0}

    def runner(args):
        calls["runner"] += 1
        return json.dumps(SAMPLE_INFO)  # only the -J metadata call should happen

    def caption_fetcher(video_id, langs):
        assert video_id == "abc123"
        return [Segment("hello from api", 7)]

    m = fetch.fetch_video_meta("https://youtu.be/abc123", runner=runner,
                               caption_fetcher=caption_fetcher)
    assert m.caption_text == "hello from api"
    assert m.caption_segments[0].t_sec == 7
    assert calls["runner"] == 1  # no second (yt-dlp caption) call — api was enough


def test_parse_vtt_strips_inline_tags():
    vtt = (
        "WEBVTT\n\n"
        "00:00:05.000 --> 00:00:07.000\n"
        "<00:00:05.120><c> hello</c><00:00:06.000><c> world</c>\n"
    )
    segs = fetch.parse_vtt(vtt)
    assert len(segs) == 1
    assert segs[0].text == "hello world"
    assert "<" not in segs[0].text


def test_ytdlp_invoked_as_module_not_path_dependent():
    # Must call `python -m yt_dlp` so it works even when the yt-dlp script
    # isn't on PATH (common with `pip install --user` on Windows).
    cmd = fetch._ytdlp("-J", "x")
    assert cmd[:3] == [sys.executable, "-m", "yt_dlp"]
    assert cmd[3:] == ["-J", "x"]


def test_caption_failure_everywhere_falls_back_to_no_caption():
    # api returns nothing AND the yt-dlp VTT fallback errors -> still no crash,
    # meta has no caption so the pipeline falls back to Whisper.
    info = dict(SAMPLE_INFO)
    info["automatic_captions"] = {"en": [{"ext": "vtt"}]}
    calls = {"n": 0}

    def runner(args):
        calls["n"] += 1
        if calls["n"] == 1:
            return json.dumps(info)          # the -J metadata call succeeds
        raise RuntimeError("subtitle fetch exploded")  # the yt-dlp caption call fails

    m = fetch.fetch_video_meta("https://youtu.be/abc123", runner=runner,
                               caption_fetcher=lambda vid, langs: [])  # api: nothing
    assert m.video_id == "abc123"
    assert m.caption_text is None
    assert calls["n"] == 2  # it attempted the yt-dlp caption fallback too
