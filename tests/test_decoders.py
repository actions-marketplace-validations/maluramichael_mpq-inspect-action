"""Unit tests for the DBC decoders — run without needing a real MPQ.

    python -m pytest tests/           (or: python tests/test_decoders.py)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from decoders.charbaseinfo import CharBaseInfoDecoder      # noqa: E402
from decoders.charstartoutfit import CharStartOutfitDecoder  # noqa: E402
from decoders.dbc import GenericDbcDecoder                 # noqa: E402


def _make_charbaseinfo(combos):
    """Build a minimal CharBaseInfo.dbc blob (2 bytes/record)."""
    rec_size = 2
    body = b"".join(bytes([r, c]) for r, c in combos)
    header = b"WDBC" + struct.pack("<4I", len(combos), 2, rec_size, 0)
    return header + body


def test_charbaseinfo_flags_new_combos():
    combos = [
        (1, 1),   # Human Warrior  -> standard
        (1, 3),   # Human Hunter   -> NEW
        (7, 5),   # Gnome Priest   -> NEW
        (5, 2),   # Undead Paladin -> NEW
        (2, 3),   # Orc Hunter     -> standard
    ]
    blob = _make_charbaseinfo(combos)
    out = CharBaseInfoDecoder().render("CharBaseInfo.dbc", blob)
    assert "Human Hunter" in out
    assert "Gnome Priest" in out
    assert "Undead Paladin" in out
    assert "Human Warrior" not in out      # standard -> not listed as new
    assert "3 non-standard" in out


def test_charbaseinfo_all_standard():
    blob = _make_charbaseinfo([(1, 1), (2, 3)])
    out = CharBaseInfoDecoder().render("CharBaseInfo.dbc", blob)
    assert "nothing added" in out


def _make_charstartoutfit(entries):
    """Build a minimal CharStartOutfit.dbc blob (74 uint32 cols/record)."""
    n_cols = 74
    rec_size = n_cols * 4
    body = b""
    for idx, (race, cls, gender, items) in enumerate(entries):
        cols = [idx, race | (cls << 8) | (gender << 16)]
        slots = (items + [0xFFFFFFFF] * 24)[:24]
        cols += slots + [0xFFFFFFFF] * (n_cols - len(cols) - 24)
        body += struct.pack(f"<{n_cols}I", *cols)
    header = b"WDBC" + struct.pack("<4I", len(entries), n_cols, rec_size, 0)
    return header + body


def test_charstartoutfit_lists_only_nonstandard():
    entries = [
        (1, 1, 0, [38, 39, 25]),       # Human Warrior -> standard, skipped
        (5, 2, 0, [45, 43, 6948]),     # Undead Paladin -> NEW
        (1, 3, 1, [148, 117, 0]),      # Human Hunter (female) -> NEW, 0 filtered
    ]
    out = CharStartOutfitDecoder().render("CharStartOutfit.dbc", _make_charstartoutfit(entries))
    assert "Undead Paladin" in out
    assert "45, 43, 6948" in out
    assert "148, 117" in out and "148, 117, 0" not in out  # 0 dropped
    assert "Human Warrior" not in out                       # standard -> skipped
    assert "2 for non-standard combos" in out


def test_generic_dbc_header():
    blob = b"WDBC" + struct.pack("<4I", 10, 4, 16, 32) + b"\x00" * (10 * 16 + 32)
    out = GenericDbcDecoder().render("SomeOther.dbc", blob)
    assert "10" in out and "WDBC" in out


if __name__ == "__main__":
    test_charbaseinfo_flags_new_combos()
    test_charbaseinfo_all_standard()
    test_charstartoutfit_lists_only_nonstandard()
    test_generic_dbc_header()
    print("all tests passed")
