"""Preview text-ish files that show up in client patches (Lua, XML, TOC, TXT)."""
from __future__ import annotations

TEXT_EXT = (".lua", ".xml", ".txt", ".toc", ".sql", ".json", ".wtf")
MAX_LINES = 40
MAX_CHARS = 4000


class TextDecoder:
    def matches(self, filename: str) -> bool:
        return filename.lower().endswith(TEXT_EXT)

    def render(self, filename: str, data: bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", "replace")
        clipped = False
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
            clipped = True
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            lines = lines[:MAX_LINES]
            clipped = True
        body = "\n".join(lines)
        note = "\n… _(truncated)_" if clipped else ""
        return (f"**`{filename}`**: {len(data):,} B\n\n"
                f"```\n{body}\n```{note}\n")
