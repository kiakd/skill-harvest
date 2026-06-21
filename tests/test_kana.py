# tests/test_kana.py
import kana


def test_to_katakana_shifts_codepoints():
    assert kana.to_katakana("か") == "カ"
    assert kana.to_katakana("ん") == "ン"
    assert kana.to_katakana("を") == "ヲ"
    assert kana.to_katakana("きゃ") == "キャ"   # yoon (2 chars) both shift


def test_six_decks_with_expected_ids():
    ids = [d["id"] for d in kana.decks()]
    assert ids == [
        "kana_hira_basic", "kana_hira_dakuten", "kana_hira_yoon",
        "kana_kata_basic", "kana_kata_dakuten", "kana_kata_yoon",
    ]


def test_deck_counts_are_complete():
    by_id = {d["id"]: d for d in kana.decks()}
    assert len(by_id["kana_hira_basic"]["cards"]) == 46
    assert len(by_id["kana_hira_dakuten"]["cards"]) == 25   # 20 dakuten + 5 handakuten
    assert len(by_id["kana_hira_yoon"]["cards"]) == 33
    assert len(by_id["kana_kata_basic"]["cards"]) == 46
    assert len(by_id["kana_kata_dakuten"]["cards"]) == 25
    assert len(by_id["kana_kata_yoon"]["cards"]) == 33


def test_cards_have_front_and_romaji_meaning_no_dupes():
    for d in kana.decks():
        fronts = [c["front"] for c in d["cards"]]
        assert len(fronts) == len(set(fronts)), f"dup in {d['id']}"
        for c in d["cards"]:
            assert c["front"] and c["meaning"]
            assert "reading" not in c or c["reading"] == ""  # front stays clean for recall


def test_katakana_deck_is_katakana_of_hiragana():
    by_id = {d["id"]: d for d in kana.decks()}
    hira = by_id["kana_hira_basic"]["cards"]
    kata = by_id["kana_kata_basic"]["cards"]
    # same romaji order, fronts are the katakana of the hiragana
    assert [c["meaning"] for c in hira] == [c["meaning"] for c in kata]
    assert kata[5]["front"] == kana.to_katakana(hira[5]["front"])


def test_build_cards_are_japanese_flashcards():
    cards = kana.build_cards(harvested_at="2026-06-21")
    assert len(cards) == 6
    for c in cards:
        assert c.category == "japanese"
        assert c.kind == "flashcards"
        assert c.flashcards  # non-empty
