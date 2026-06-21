# tests/test_config.py
import config


def test_categories_have_required_fields():
    for c in config.CATEGORIES:
        assert "id" in c and "label" in c
        assert c["id"] and c["label"]


def test_other_category_always_present():
    assert "other" in config.category_ids()


def test_normalize_category_keeps_valid_id():
    assert config.normalize_category("pixel-art") == "pixel-art"


def test_normalize_category_falls_back_to_other():
    assert config.normalize_category("nonexistent") == "other"
    assert config.normalize_category(None) == "other"


def test_is_valid_category():
    assert config.is_valid_category("unity") is True
    assert config.is_valid_category("made-up") is False
