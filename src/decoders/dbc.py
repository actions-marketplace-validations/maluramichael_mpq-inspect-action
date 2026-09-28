"""Generic DBC (WDBC) support: header parsing shared by all DBC decoders."""
from __future__ import annotations

import struct
from typing import List, Tuple


class DbcFile:
    """Parsed WDBC container: header + raw record blob + string block."""

    def __init__(self, blob: bytes):
        if blob[:4] != b"WDBC":
            raise ValueError("not a WDBC file")
        (self.record_count, self.field_count,
         self.record_size, self.string_size) = struct.unpack_from("<4I", blob, 4)
        start = 20
        end = start + self.record_count * self.record_size
        self.records_blob = blob[start:end]
        self.string_block = blob[end:end + self.string_size]

    def rows(self) -> List[bytes]:
        rs = self.record_size
        return [self.records_blob[i * rs:(i + 1) * rs]
                for i in range(self.record_count)]

    def uint32_columns(self, row: bytes) -> Tuple[int, ...]:
        n = len(row) // 4
        return struct.unpack_from(f"<{n}I", row, 0)


class GenericDbcDecoder:
    """Fallback for any *.dbc we have no specific decoder for: report shape."""

    def matches(self, filename: str) -> bool:
        return filename.lower().endswith(".dbc")

    def render(self, filename: str, data: bytes):
        try:
            dbc = DbcFile(data)
        except ValueError:
            return None
        return (
            f"**`{filename}`**: WDBC: "
            f"{dbc.record_count:,} records · {dbc.field_count} fields · "
            f"{dbc.record_size} B/record · {dbc.string_size:,} B strings\n"
        )
