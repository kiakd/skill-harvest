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
            text = re.sub(r"<[^>]+>", "", text)          # strip inline VTT/HTML tags
            text = re.sub(r"\s+", " ", text).strip()     # collapse whitespace
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
            "--sub-lang", lang, "--sub-format", "vtt", "-o", "subtitle:-", url,
        ])
        segs = parse_vtt(vtt)
        if segs:
            meta.caption_segments = segs
            meta.caption_text = " ".join(s.text for s in segs)
    return meta
