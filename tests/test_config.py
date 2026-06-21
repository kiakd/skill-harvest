# tests/test_config.py
import os

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


def test_load_dotenv_sets_missing_but_never_overrides(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# a comment\n'
        'SH_FROM_DOTENV="hello"\n'
        'SH_ALREADY_SET=from-dotenv\n'
        'bad line without equals\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("SH_FROM_DOTENV", raising=False)
    monkeypatch.setenv("SH_ALREADY_SET", "from-real-env")

    config._load_dotenv(str(env_file))

    assert os.environ["SH_FROM_DOTENV"] == "hello"          # quotes stripped, value set
    assert os.environ["SH_ALREADY_SET"] == "from-real-env"  # real env wins, not overridden
    os.environ.pop("SH_FROM_DOTENV", None)  # avoid leaking into other tests


def test_load_dotenv_missing_file_is_noop():
    config._load_dotenv("this-file-does-not-exist.env")  # must not raise
