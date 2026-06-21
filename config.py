# config.py
"""Central settings + category registry. Settings read from env with defaults."""
import os


def _load_dotenv(path=".env"):
    """Load KEY=VALUE lines from a .env file into os.environ.

    Keeps secrets (e.g. a DeepSeek API key) out of the repo: put them in .env
    (gitignored) and they are picked up automatically. Existing env vars win —
    .env never overrides something already set in the real environment.
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# --- LLM (OpenAI-compatible endpoint). Default = local Gemma 4 via Ollama. ---
# Switch to DeepSeek/OpenRouter by setting these in .env or the environment.
LLM_BASE_URL = os.environ.get("SH_LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.environ.get("SH_LLM_API_KEY", "ollama")
LLM_MODEL = os.environ.get("SH_LLM_MODEL", "gemma4:e4b")

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
