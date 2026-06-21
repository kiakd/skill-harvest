# tests/test_store.py
import json
import os
import store
from models import Card


def make_card(vid="abc", category="pixel-art"):
    return Card(
        id=f"yt_{vid}", title="T", source_url=f"https://youtu.be/{vid}", channel="C",
        duration_sec=100, category=category, category_source="ai", tags=["aseprite"],
        harvested_at="2026-06-21", transcript_source="caption", summary="s",
        tools=["Aseprite"], steps=[{"text": "x", "t_sec": 5}], tips=["t"],
        glossary=[{"term": "smear", "meaning": "m"}], visual_gap=False,
    )


def _point_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(store.config, "CARDS_DIR", str(tmp_path / "cards"))
    monkeypatch.setattr(store.config, "CARDS_DATA_JS", str(tmp_path / "cards-data.js"))
    monkeypatch.setattr(store.config, "GALLERY_HTML", str(tmp_path / "gallery.html"))


def test_write_card_creates_json(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.write_card(make_card("abc"))
    path = tmp_path / "cards" / "yt_abc.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["category"] == "pixel-art"


def test_regenerate_embeds_all_cards(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.write_card(make_card("abc", "pixel-art"))
    store.write_card(make_card("def", "unity"))
    store.regenerate_cards_data()

    js = (tmp_path / "cards-data.js").read_text(encoding="utf-8")
    assert js.startswith("window.CARDS =")
    # The embedded payload must be valid JSON when the prefix/suffix are stripped.
    payload = js[len("window.CARDS = "):].rstrip().rstrip(";")
    cards = json.loads(payload)
    assert len(cards) == 2
    assert {c["category"] for c in cards} == {"pixel-art", "unity"}


def test_store_card_copies_gallery_template(tmp_path, monkeypatch):
    _point_dirs(monkeypatch, tmp_path)
    store.store_card(make_card("abc"))
    assert (tmp_path / "gallery.html").exists()
    assert (tmp_path / "cards-data.js").exists()
