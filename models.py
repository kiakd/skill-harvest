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
