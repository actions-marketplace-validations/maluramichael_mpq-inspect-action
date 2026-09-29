"""Decoder for CharTitles.dbc — the player titles a patch ships (e.g. a prestige
mod adds custom ones). We list Id + enUS title text.

3.3.5a layout (37 cols / 148 B): col 0 = Id, col 2 = enUS Name_lang offset
(the name templates carry a "%s" placeholder for the character name).
"""
from __future__ import annotations

from .dbc import DbcFile

_NAME_COL = 2
_MAX_ROWS = 40


class CharTitlesDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("chartitles.dbc")

    def render(self, filename: str, data: bytes):
        try:
            dbc = DbcFile(data)
        except ValueError:
            return None
        if dbc.record_size < (_NAME_COL + 1) * 4:
            return None

        rows = []
        for row in dbc.rows():
            cols = dbc.uint32_columns(row)
            name = dbc.cstring(cols[_NAME_COL]).replace("%s", "…").strip()
            rows.append((cols[0], name or "_?_"))

        lines = [f"**`{filename}`: {len(rows)} titles**\n"]
        lines.append("| Id | Title |")
        lines.append("|---:|-------|")
        for rid, name in rows[:_MAX_ROWS]:
            lines.append(f"| {rid} | {name} |")
        if len(rows) > _MAX_ROWS:
            lines.append(f"| … | _{len(rows) - _MAX_ROWS} more_ |")
        lines.append("")
        return "\n".join(lines)
