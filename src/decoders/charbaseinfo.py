"""Decoder for CharBaseInfo.dbc — the file that gates which race/class combos
the 3.3.5a client offers at character creation.

Record layout: 2 bytes per row (raceId u8, classId u8). We decode every combo
and diff it against the standard WotLK matrix, so the report highlights exactly
which combos a client patch newly enables.
"""
from __future__ import annotations

import struct

RACES = {
    1: "Human", 2: "Orc", 3: "Dwarf", 4: "Night Elf", 5: "Undead",
    6: "Tauren", 7: "Gnome", 8: "Troll", 9: "Goblin", 10: "Blood Elf",
    11: "Draenei",
}
CLASSES = {
    1: "Warrior", 2: "Paladin", 3: "Hunter", 4: "Rogue", 5: "Priest",
    6: "Death Knight", 7: "Shaman", 8: "Mage", 9: "Warlock", 11: "Druid",
}

# Standard WotLK (3.3.5a) race/class matrix. Death Knight (6) is valid for
# every race at 55+, so it counts as standard everywhere.
STANDARD = {
    1: {1, 2, 4, 5, 8, 9},   2: {1, 3, 4, 7, 9},
    3: {1, 2, 3, 4, 5},      4: {1, 3, 4, 5, 11},
    5: {1, 4, 5, 8, 9},      6: {1, 3, 7, 11},
    7: {1, 4, 8, 9},         8: {1, 3, 4, 5, 7, 8},
    10: {2, 3, 4, 5, 8, 9},  11: {1, 2, 3, 5, 7, 8},
}


def _is_standard(race: int, cls: int) -> bool:
    return cls == 6 or cls in STANDARD.get(race, set())


def _rname(r: int) -> str:
    return RACES.get(r, f"Race {r}")


def _cname(c: int) -> str:
    return CLASSES.get(c, f"Class {c}")


class CharBaseInfoDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("charbaseinfo.dbc")

    def render(self, filename: str, data: bytes):
        if data[:4] != b"WDBC":
            return None
        rec_count, _field_count, rec_size, _string_size = struct.unpack_from(
            "<4I", data, 4)
        combos = set()
        off = 20
        for _ in range(rec_count):
            rec = data[off:off + rec_size]
            if len(rec) < 2:
                break
            combos.add((rec[0], rec[1]))
            off += rec_size

        combos = sorted(combos)
        new = [(r, c) for (r, c) in combos if not _is_standard(r, c)]
        lines = [
            f"**`{filename}`: {len(combos)} race/class combos, "
            f"{len(new)} non-standard**\n"
        ]
        if new:
            lines.append("| ✨ New combo | race | class |")
            lines.append("|-------------|:----:|:-----:|")
            for r, c in new:
                lines.append(f"| **{_rname(r)} {_cname(c)}** | {r} | {c} |")
        else:
            lines.append("_All combos are standard WotLK, nothing added._")
        lines.append("")
        return "\n".join(lines)
