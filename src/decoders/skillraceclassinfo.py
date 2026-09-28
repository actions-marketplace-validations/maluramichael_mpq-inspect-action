"""Decoder for SkillRaceClassInfo.dbc — the table that gates which race/class
gets which skill. This is exactly what "combos" mods edit to hand new race/class
pairs their weapon and armor proficiencies (the Undead-Paladin-can't-use-swords
class of bug).

3.3.5a layout (32 B / 8 uint32 columns):
    col 0  Id
    col 1  SkillLineID
    col 2  RaceMask   (bit race-1; 0xFFFFFFFF = all)
    col 3  ClassMask  (bit class-1; 0xFFFFFFFF = all)
    col 4  Flags
    col 5  MinLevel
    col 6  SkillTierID
    col 7  SkillCostIndex

We surface the proficiency-style rows (a small class set restricted to a subset
of races), which is where these patches live. Broad all-race/all-class spell and
racial rows are dropped as noise. Skill/class/race IDs come from the fixed WotLK
tables; skill *names* would need SkillLine.dbc, which patches rarely ship.
"""
from __future__ import annotations

from .charbaseinfo import CLASSES, RACES
from .dbc import DbcFile

_RACE_IDS = [r for r in RACES]      # 1..11
_CLASS_IDS = [c for c in CLASSES]   # 1..9, 11
_MAX_ROWS = 80


def _names(mask: int, ids, table) -> list:
    return [table[i] for i in ids if mask & (1 << (i - 1))]


class SkillRaceClassInfoDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith("skillraceclassinfo.dbc")

    def render(self, filename: str, data: bytes):
        try:
            dbc = DbcFile(data)
        except ValueError:
            return None
        if dbc.record_size < 16:  # need at least Id..Flags
            return None

        rows = []
        for row in dbc.rows():
            cols = dbc.uint32_columns(row)
            if len(cols) < 4:
                continue
            skill, race_mask, class_mask = cols[1], cols[2], cols[3]
            classes = _names(class_mask, _CLASS_IDS, CLASSES)
            races = _names(race_mask, _RACE_IDS, RACES)
            # proficiency-style: few classes, race-restricted (not every race)
            if 0 < len(classes) <= 4 and 0 < len(races) < len(_RACE_IDS):
                rows.append((skill, classes, races))

        lines = [
            f"**`{filename}`: {dbc.record_count} skill rows, "
            f"{len(rows)} race-restricted proficiency-style**\n"
        ]
        if not rows:
            lines.append("_No race-restricted proficiency rows._")
            lines.append("")
            return "\n".join(lines)

        lines.append("| Skill | Classes | Races |")
        lines.append("|------:|---------|-------|")
        for skill, classes, races in rows[:_MAX_ROWS]:
            lines.append(f"| {skill} | {', '.join(classes)} | {', '.join(races)} |")
        if len(rows) > _MAX_ROWS:
            lines.append(f"| … | _{len(rows) - _MAX_ROWS} more_ | |")
        lines.append("")
        return "\n".join(lines)
