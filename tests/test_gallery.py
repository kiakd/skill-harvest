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
