"""Decoders for ChrClasses.dbc and ChrRaces.dbc — the class and race definition
tables. Both start with an Id and carry a localized name; we surface Id + enUS
name, so a custom class/race a mod adds shows up as a new row a reviewer can
eyeball.

Verified 3.3.5a column offsets of the enUS Name_lang field (first locale slot):
    ChrClasses.dbc  60 cols / 240 B  -> name at col 4
    ChrRaces.dbc    69 cols / 276 B  -> name at col 14
"""
from __future__ import annotations

from .dbc import DbcFile


def _render(filename, data, kind, name_col):
    try:
        dbc = DbcFile(data)
    except ValueError:
        return None
    if dbc.record_size < (name_col + 1) * 4:
        return None  # unexpected layout -> let the generic decoder handle it

    rows = [(cols[0], dbc.cstring(cols[name_col]) or "_?_")
            for cols in (dbc.uint32_columns(r) for r in dbc.rows())]

    lines = [f"**`{filename}`: {len(rows)} {kind}**\n", "| Id | Name |", "|---:|------|"]
    lines += [f"| {rid} | {name} |" for rid, name in rows]
    lines.append("")
    return "\n".join(lines)


class ChrClassesDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("chrclasses.dbc")

    def render(self, filename: str, data: bytes):
        return _render(filename, data, "classes", 4)


class ChrRacesDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("chrraces.dbc")

    def render(self, filename: str, data: bytes):
        return _render(filename, data, "races", 14)
