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
