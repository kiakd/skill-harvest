# cli.py
"""Entrypoint: harvest a YouTube link into a knowledge card."""
import argparse
import datetime
import sys

import config
import fetch
import transcribe
import summarize as summarize_mod
import store as store_mod


def validate_category(cat_id):
    """Return cat_id if valid or None; exit with error if an unknown id is given."""
    if cat_id is None:
        return None
    if not config.is_valid_category(cat_id):
        valid = ", ".join(sorted(config.category_ids()))
        sys.stderr.write(f"error: ไม่รู้จักหมวด '{cat_id}'. หมวดที่มี: {valid}\n")
        raise SystemExit(2)
    return cat_id


def run_pipeline(url, manual_category, harvested_at,
                 fetch_fn=None, transcript_fn=None, summarize_fn=None, store_fn=None):
    """fetch -> transcript -> summarize -> store. Deps injected for testing."""
    fetch_fn = fetch_fn or fetch.fetch_video_meta
    transcript_fn = transcript_fn or transcribe.get_transcript
    summarize_fn = summarize_fn or summarize_mod.summarize
    store_fn = store_fn or store_mod.store_card

    meta = fetch_fn(url)
    transcript = transcript_fn(meta)
    card = summarize_fn(meta, transcript, harvested_at=harvested_at,
                        manual_category=manual_category)
    store_fn(card)
    return card


def _force_utf8_streams():
    """Ensure Thai output/errors don't crash on a Windows cp1252 console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure and getattr(stream, "encoding", "").lower() != "utf-8":
            reconfigure(encoding="utf-8")


def main(argv=None):
    _force_utf8_streams()

    parser = argparse.ArgumentParser(prog="harvest", description="สรุปทูตอเรียล YouTube เป็นการ์ดความรู้")
    parser.add_argument("url", help="ลิงก์ YouTube")
    parser.add_argument("--category", default=None,
                        help="กำหนดหมวดเอง (override AI). ต้องเป็น id ที่มีใน config")
    args = parser.parse_args(argv)

    manual_category = validate_category(args.category)
    harvested_at = datetime.date.today().isoformat()

    card = run_pipeline(args.url, manual_category=manual_category, harvested_at=harvested_at)
    print(f"✓ การ์ด {card.id} [{card.category}] -> {config.CARDS_DIR}/{card.id}.json")
    print(f"  เปิดดูคลัง: {config.GALLERY_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
