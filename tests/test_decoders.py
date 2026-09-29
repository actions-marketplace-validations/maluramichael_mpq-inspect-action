"""Unit tests for the DBC decoders — run without needing a real MPQ.

    python -m pytest tests/           (or: python tests/test_decoders.py)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from decoders.charbaseinfo import CharBaseInfoDecoder      # noqa: E402
from decoders.charstartoutfit import CharStartOutfitDecoder  # noqa: E402
from decoders.chartitles import CharTitlesDecoder           # noqa: E402
from decoders.chrinfo import ChrClassesDecoder, ChrRacesDecoder  # noqa: E402
from decoders.dbc import GenericDbcDecoder                 # noqa: E402
from decoders.skillraceclassinfo import SkillRaceClassInfoDecoder  # noqa: E402


def _make_dbc(rows, n_cols, string_block=b"\x00"):
    """Build a WDBC blob from rows of uint32 columns + a string block."""
    rec_size = n_cols * 4
    body = b"".join(struct.pack(f"<{n_cols}I", *r) for r in rows)
    header = b"WDBC" + struct.pack("<4I", len(rows), n_cols, rec_size, len(string_block))
    return header + body + string_block


def _strings(*names):
    """Pack names into a string block; return (block, {name: offset})."""
    block = b"\x00"
    offsets = {}
    for name in names:
        offsets[name] = len(block)
        block += name.encode("utf-8") + b"\x00"
    return block, offsets


def test_skillraceclassinfo_shows_restricted_proficiencies():
    ALL = 0xFFFFFFFF
    rows = [
        (1, 43, 1 | 4 | 16, 2, 0, 0, 0, 0),   # Axes, Paladin, Human+Dwarf+Undead
        (2, 95, ALL, ALL, 0, 0, 0, 0),         # all races/classes -> dropped as noise
    ]
    out = SkillRaceClassInfoDecoder().render("SkillRaceClassInfo.dbc", _make_dbc(rows, 8))
    assert "1 race-restricted" in out
    assert "| 43 | Paladin | Human, Dwarf, Undead |" in out
    assert "| 95 " not in out                  # all-race/all-class row excluded


def test_chrclasses_lists_names():
    block, off = _strings("Warrior", "Paladin")
    rows = [
        [1] + [0, 0, 0, off["Warrior"]] + [0] * 55,
        [2] + [0, 0, 0, off["Paladin"]] + [0] * 55,
    ]
    out = ChrClassesDecoder().render("ChrClasses.dbc", _make_dbc(rows, 60, block))
    assert "2 classes" in out
    assert "| 1 | Warrior |" in out and "| 2 | Paladin |" in out


def test_chrraces_reads_name_at_col14():
    block, off = _strings("Human")
    row = [1] + [0] * 13 + [off["Human"]] + [0] * 54   # name at col 14
    out = ChrRacesDecoder().render("ChrRaces.dbc", _make_dbc([row], 69, block))
    assert "| 1 | Human |" in out


def test_chartitles_reads_name_at_col2():
    block, off = _strings("Private %s")
    row = [1, 0, off["Private %s"]] + [0] * 34   # name at col 2
    out = CharTitlesDecoder().render("CharTitles.dbc", _make_dbc([row], 37, block))
    assert "Private" in out and "1 titles" in out


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
    # each item id becomes a plain Wowhead link, no network request
    assert "[6948](https://www.wowhead.com/wotlk/item=6948)" in out
    assert "[0]" not in out                             # 0 slot dropped
    assert "Human Warrior" not in out                   # standard -> skipped
    assert "2 for non-standard combos" in out


def test_generic_dbc_header():
    blob = b"WDBC" + struct.pack("<4I", 10, 4, 16, 32) + b"\x00" * (10 * 16 + 32)
    out = GenericDbcDecoder().render("SomeOther.dbc", blob)
    assert "10" in out and "WDBC" in out


if __name__ == "__main__":
    test_charbaseinfo_flags_new_combos()
    test_charbaseinfo_all_standard()
    test_charstartoutfit_lists_only_nonstandard()
    test_skillraceclassinfo_shows_restricted_proficiencies()
    test_chrclasses_lists_names()
    test_chrraces_reads_name_at_col14()
    test_chartitles_reads_name_at_col2()
    test_generic_dbc_header()
    print("all tests passed")
