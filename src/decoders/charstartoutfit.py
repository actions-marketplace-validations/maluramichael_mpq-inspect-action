"""Decoder for CharStartOutfit.dbc — the starting gear a new character spawns
with, keyed by race/class/gender.

3.3.5a record layout (296 B / 74 uint32 columns):
    col 0      Id
    col 1      packed: race = b0, class = b1, gender = b2, outfit = b3
    col 2..25  ItemID[24]
    col 26..49 DisplayInfoID[24]
    col 50..73 InventoryType[24]

We list the item IDs per combo, but only for NON-standard race/class pairs
(the ones a combos mod newly enables), reusing the WotLK matrix from the
CharBaseInfo decoder so the table stays small and on-topic.
"""
from __future__ import annotations

import struct

from .charbaseinfo import _cname, _is_standard, _rname

_SEX = {0: "♂", 1: "♀", 2: "both"}
_EMPTY = (0, 0xFFFFFFFF)
# plain link to Wowhead's WotLK item page; no request, the ID just goes in.
_ITEM_URL = "https://www.wowhead.com/wotlk/item={0}"


class CharStartOutfitDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("charstartoutfit.dbc")

    def render(self, filename: str, data: bytes):
        if data[:4] != b"WDBC":
            return None
        rec_count, _fields, rec_size, _strings = struct.unpack_from("<4I", data, 4)
        if rec_size < 26 * 4:  # need at least the 24 item slots
            return None
        n_cols = rec_size // 4
        off = 20
        rows = []
        for _ in range(rec_count):
            cols = struct.unpack_from(f"<{n_cols}I", data, off)
            off += rec_size
            packed = cols[1]
            race, cls = packed & 0xFF, (packed >> 8) & 0xFF
            if _is_standard(race, cls):
                continue
            gender = (packed >> 16) & 0xFF
            items = [c for c in cols[2:26] if c not in _EMPTY]
            rows.append((race, cls, gender, items))

        lines = [
            f"**`{filename}`: {rec_count} outfits, "
            f"{len(rows)} for non-standard combos**\n"
        ]
        if rows:
            lines.append("| Combo | Sex | Starting items |")
            lines.append("|-------|:---:|----------------|")
            for race, cls, gender, items in rows:
                cell = ", ".join(
                    f"[{i}]({_ITEM_URL.format(i)})" for i in items
                ) or "_none_"
                lines.append(
                    f"| **{_rname(race)} {_cname(cls)}** | "
                    f"{_SEX.get(gender, gender)} | {cell} |"
                )
        else:
            lines.append("_No outfits for non-standard combos._")
        lines.append("")
        return "\n".join(lines)
