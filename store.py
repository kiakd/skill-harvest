# store.py
"""Persist cards as JSON (source of truth) and regenerate gallery data."""
import glob
import json
import os
import shutil

import config

_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates", "gallery.html")


def write_card(card):
    """Write a single card to cards/<id>.json."""
    os.makedirs(config.CARDS_DIR, exist_ok=True)
    path = os.path.join(config.CARDS_DIR, f"{card.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def _load_all_cards():
    cards = []
    for path in sorted(glob.glob(os.path.join(config.CARDS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            cards.append(json.load(f))
    return cards


def regenerate_cards_data():
    """Rebuild cards-data.js (window.CARDS = [...]) from all card JSON files."""
    cards = _load_all_cards()
    payload = json.dumps(cards, ensure_ascii=False, indent=2)
    with open(config.CARDS_DATA_JS, "w", encoding="utf-8") as f:
        f.write(f"window.CARDS = {payload};\n")
    return config.CARDS_DATA_JS


def ensure_gallery():
    """Copy the gallery template next to cards-data.js if not already present."""
    if not os.path.exists(config.GALLERY_HTML):
        shutil.copyfile(_TEMPLATE, config.GALLERY_HTML)
    return config.GALLERY_HTML


def store_card(card):
    """Full store step: write card JSON, regenerate data, ensure gallery exists."""
    write_card(card)
    regenerate_cards_data()
    ensure_gallery()
