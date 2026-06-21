# kana.py
"""Generate complete Hiragana + Katakana flashcard decks (reference data, not from
a video). Six decks: hiragana/katakana × basic(gojuon) / dakuten+handakuten / yoon.

Each flashcard is {front: <kana>, meaning: <romaji>} — the front stays just the
kana so the gallery flip is a real recall test; the romaji is revealed on flip.
Katakana is derived from hiragana by shifting each codepoint by 0x60, which is
exact across the Unicode kana blocks (incl. small ゃゅょ and ん/を).

Run `python kana.py` to write the decks into the cards library + regenerate the
gallery data.
"""
import datetime

from models import Card

# Gojuon — 46 basic hiragana with romaji (irregulars spelled out: shi/chi/tsu/fu/wo/n).
GOJUON = [
    ("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o"),
    ("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko"),
    ("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so"),
    ("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to"),
    ("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no"),
    ("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho"),
    ("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo"),
    ("や", "ya"), ("ゆ", "yu"), ("よ", "yo"),
    ("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro"),
    ("わ", "wa"), ("を", "wo"),
    ("ん", "n"),
]

# Dakuten (゛) + handakuten (゜) — 20 + 5 = 25.
DAKUTEN = [
    ("が", "ga"), ("ぎ", "gi"), ("ぐ", "gu"), ("げ", "ge"), ("ご", "go"),
    ("ざ", "za"), ("じ", "ji"), ("ず", "zu"), ("ぜ", "ze"), ("ぞ", "zo"),
    ("だ", "da"), ("ぢ", "ji"), ("づ", "zu"), ("で", "de"), ("ど", "do"),
    ("ば", "ba"), ("び", "bi"), ("ぶ", "bu"), ("べ", "be"), ("ぼ", "bo"),
    ("ぱ", "pa"), ("ぴ", "pi"), ("ぷ", "pu"), ("ぺ", "pe"), ("ぽ", "po"),
]

# Yoon — contracted sounds with small ゃゅょ. 11 rows × 3 = 33.
YOON = [
    ("きゃ", "kya"), ("きゅ", "kyu"), ("きょ", "kyo"),
    ("しゃ", "sha"), ("しゅ", "shu"), ("しょ", "sho"),
    ("ちゃ", "cha"), ("ちゅ", "chu"), ("ちょ", "cho"),
    ("にゃ", "nya"), ("にゅ", "nyu"), ("にょ", "nyo"),
    ("ひゃ", "hya"), ("ひゅ", "hyu"), ("ひょ", "hyo"),
    ("みゃ", "mya"), ("みゅ", "myu"), ("みょ", "myo"),
    ("りゃ", "rya"), ("りゅ", "ryu"), ("りょ", "ryo"),
    ("ぎゃ", "gya"), ("ぎゅ", "gyu"), ("ぎょ", "gyo"),
    ("じゃ", "ja"), ("じゅ", "ju"), ("じょ", "jo"),
    ("びゃ", "bya"), ("びゅ", "byu"), ("びょ", "byo"),
    ("ぴゃ", "pya"), ("ぴゅ", "pyu"), ("ぴょ", "pyo"),
]

_HIRA_TO_KATA_OFFSET = 0x60


def to_katakana(hira):
    """Convert a hiragana string to katakana by shifting each codepoint by 0x60."""
    return "".join(chr(ord(c) + _HIRA_TO_KATA_OFFSET) for c in hira)


def _cards(rows, katakana=False):
    out = []
    for hira, romaji in rows:
        front = to_katakana(hira) if katakana else hira
        out.append({"front": front, "meaning": romaji})
    return out


def decks():
    """Return the six flashcard decks as dicts: {id, title, summary, tags, cards}."""
    return [
        {"id": "kana_hira_basic", "title": "ฮิรางานะ — พื้นฐาน (ごじゅうおん)",
         "summary": "ฮิรางานะพื้นฐาน 46 ตัว", "tags": ["hiragana", "kana", "basic"],
         "cards": _cards(GOJUON)},
        {"id": "kana_hira_dakuten", "title": "ฮิรางานะ — ดะคุเต็น/ฮันดะคุเต็น (が ぱ)",
         "summary": "ฮิรางานะเสียงขุ่น/กึ่งขุ่น 25 ตัว", "tags": ["hiragana", "kana", "dakuten"],
         "cards": _cards(DAKUTEN)},
        {"id": "kana_hira_yoon", "title": "ฮิรางานะ — โยอง (きゃ)",
         "summary": "ฮิรางานะเสียงควบ 33 ตัว", "tags": ["hiragana", "kana", "yoon"],
         "cards": _cards(YOON)},
        {"id": "kana_kata_basic", "title": "คาตาคานะ — พื้นฐาน (ゴジュウオン)",
         "summary": "คาตาคานะพื้นฐาน 46 ตัว", "tags": ["katakana", "kana", "basic"],
         "cards": _cards(GOJUON, katakana=True)},
        {"id": "kana_kata_dakuten", "title": "คาตาคานะ — ดะคุเต็น/ฮันดะคุเต็น (ガ パ)",
         "summary": "คาตาคานะเสียงขุ่น/กึ่งขุ่น 25 ตัว", "tags": ["katakana", "kana", "dakuten"],
         "cards": _cards(DAKUTEN, katakana=True)},
        {"id": "kana_kata_yoon", "title": "คาตาคานะ — โยอง (キャ)",
         "summary": "คาตาคานะเสียงควบ 33 ตัว", "tags": ["katakana", "kana", "yoon"],
         "cards": _cards(YOON, katakana=True)},
    ]


def build_cards(harvested_at):
    """Build Card objects (japanese flashcard kind) for all six decks."""
    cards = []
    for d in decks():
        cards.append(Card(
            id=d["id"], title=d["title"], source_url="", channel="คานะ (อ้างอิง)",
            duration_sec=0, category="japanese", category_source="manual",
            tags=d["tags"], harvested_at=harvested_at, transcript_source="reference",
            summary=d["summary"], tools=[], steps=[], tips=[], glossary=[],
            kind="flashcards", flashcards=d["cards"],
        ))
    return cards


def main():
    import store
    today = datetime.date.today().isoformat()
    for card in build_cards(harvested_at=today):
        store.write_card(card)
        print(f"✓ {card.id}  ({len(card.flashcards)} cards)")
    store.regenerate_cards_data()
    store.ensure_gallery()
    print("regenerated gallery")


if __name__ == "__main__":
    main()
