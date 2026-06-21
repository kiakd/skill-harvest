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
