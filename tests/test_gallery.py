# tests/test_gallery.py
import os

GALLERY = os.path.join(os.path.dirname(__file__), "..", "templates", "gallery.html")


def test_gallery_loads_cards_data_script():
    html = open(GALLERY, encoding="utf-8").read()
    assert '<script src="cards-data.js">' in html or "<script src='cards-data.js'>" in html


def test_gallery_has_category_and_tag_filter_hooks():
    html = open(GALLERY, encoding="utf-8").read()
    assert "window.CARDS" in html
    assert 'id="category-chips"' in html
    assert 'id="tag-chips"' in html
    assert 'id="search"' in html


def test_gallery_builds_timestamp_links_from_id_not_buggy_concat():
    html = open(GALLERY, encoding="utf-8").read()
    # jump links must be built as youtu.be/<id>?t= (single "?"), and the title
    # must be a clickable link to the video.
    assert "https://youtu.be/" in html
    assert 'class="title-link"' in html
    # the old bug appended ?t= straight onto source_url (watch?v=...) -> double "?"
    assert "c.source_url + '?t='" not in html
    assert 'c.source_url + "?t="' not in html


def test_gallery_supports_flashcards_and_step_detail():
    html = open(GALLERY, encoding="utf-8").read()
    # branches on kind, with a default for old cards
    assert 'c.kind' in html
    # flashcard flip support
    assert "flip" in html
    assert "flipped" in html
    # tutorial step detail collapsible
    assert "อธิบายเพิ่ม" in html


def test_gallery_uses_category_labels_for_chips():
    html = open(GALLERY, encoding="utf-8").read()
    # chips show human labels (window.CATEGORY_LABELS) instead of raw ids
    assert "CATEGORY_LABELS" in html


def test_gallery_has_audio_and_handles_non_video_cards():
    html = open(GALLERY, encoding="utf-8").read()
    # 🔊 audio via browser TTS
    assert "speechSynthesis" in html
    assert "🔊" in html
    assert 'lang = "ja-JP"' in html
    # reference cards (id not starting yt_) must not get a youtu.be link
    assert 'id.indexOf("yt_") === 0' in html
