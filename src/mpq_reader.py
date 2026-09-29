"""MPQ loader abstraction.

Backed by mpyq (MIT, pure-Python) for header/hash/block parsing and the crypt
table, but with our own `read_file` that also handles ENCRYPTED sectors — mpyq
raises `NotImplementedError` on those, and real client patches from this mod
encrypt their `(listfile)` (MPQ_FILE_ENCRYPTED | MPQ_FILE_FIX_KEY), which made
mpyq crash on open. The rest of the tool only depends on the small interface
below, so a StormLib swap later stays a one-file change.
"""
from __future__ import annotations

import bz2
import struct
import zlib
from io import BytesIO
from typing import List, Optional

# DBCs that turn up in WoW client patches, probed by name when an archive
# ships without a (listfile). Covers the ones our decoders understand plus the
# common custom-race/class/item tables. The client stores paths with backslashes.
_KNOWN_NAMES = [
    "DBFilesClient\\" + n for n in (
        "CharBaseInfo.dbc", "CharStartOutfit.dbc", "SkillRaceClassInfo.dbc",
        "ChrClasses.dbc", "ChrRaces.dbc", "CharTitles.dbc", "CharSections.dbc",
        "AreaTable.dbc", "SkillLine.dbc", "SkillLineAbility.dbc", "Spell.dbc",
        "Item.dbc", "ItemDisplayInfo.dbc", "Talent.dbc", "TalentTab.dbc",
        "CreatureDisplayInfo.dbc", "CreatureModelData.dbc",
    )
]

MPQ_FILE_COMPRESS = 0x00000200
MPQ_FILE_ENCRYPTED = 0x00010000
MPQ_FILE_FIX_KEY = 0x00020000
MPQ_FILE_SINGLE_UNIT = 0x01000000
MPQ_FILE_SECTOR_CRC = 0x04000000
MPQ_FILE_EXISTS = 0x80000000


def _decompress(data: bytes) -> bytes:
    """Read the 1-byte compression mask and inflate a sector."""
    mask = data[0]
    if mask == 0:
        return data
    if mask == 2:
        return zlib.decompress(data[1:], 15)
    if mask == 16:
        return bz2.decompress(data[1:])
    raise RuntimeError(f"unsupported compression mask 0x{mask:02x}")


class Archive:
    """Minimal read interface over an MPQ file, encryption-aware."""

    def __init__(self, path: str):
        from mpyq import MPQArchive  # imported lazily so tests don't need it

        self._path = path
        # listfile=False: mpyq's own listfile read raises on encrypted archives.
        self._mpq = MPQArchive(path, listfile=False)
        self._enc_table = MPQArchive.encryption_table
        self._sector_size = 512 << self._mpq.header["sector_size_shift"]

    # --- MPQ crypto (standard algorithm; trailing <4-byte tail stays raw) ---
    def _decrypt(self, data: bytes, key: int) -> bytes:
        seed1 = key & 0xFFFFFFFF
        seed2 = 0xEEEEEEEE
        out = bytearray()
        n = len(data) // 4
        for i in range(n):
            seed2 = (seed2 + self._enc_table[0x400 + (seed1 & 0xFF)]) & 0xFFFFFFFF
            value = struct.unpack_from("<I", data, i * 4)[0]
            value = (value ^ (seed1 + seed2)) & 0xFFFFFFFF
            seed1 = (((~seed1 << 0x15) & 0xFFFFFFFF) + 0x11111111) | (seed1 >> 0x0B)
            seed1 &= 0xFFFFFFFF
            seed2 = (value + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
            out += struct.pack("<I", value)
        out += data[n * 4:]
        return bytes(out)

    def _file_key(self, name: str, block) -> Optional[int]:
        if not (block.flags & MPQ_FILE_ENCRYPTED):
            return None
        base = name.replace("/", "\\").split("\\")[-1]
        key = self._mpq._hash(base, "TABLE")
        if block.flags & MPQ_FILE_FIX_KEY:
            key = ((key + block.offset) ^ block.size) & 0xFFFFFFFF
        return key

    def _read_block(self, name: str, block) -> Optional[bytes]:
        if not (block.flags & MPQ_FILE_EXISTS) or block.archived_size == 0:
            return None
        self._mpq.file.seek(block.offset + self._mpq.header["offset"])
        raw = self._mpq.file.read(block.archived_size)
        key = self._file_key(name, block)

        if block.flags & MPQ_FILE_SINGLE_UNIT:
            data = self._decrypt(raw, key) if key is not None else raw
            if block.flags & MPQ_FILE_COMPRESS and block.size > block.archived_size:
                data = _decompress(data)
            return data

        sectors = block.size // self._sector_size + 1
        crc = bool(block.flags & MPQ_FILE_SECTOR_CRC)
        if crc:
            sectors += 1
        n_pos = sectors + 1
        pos_tbl = raw[: 4 * n_pos]
        if key is not None:
            pos_tbl = self._decrypt(pos_tbl, (key - 1) & 0xFFFFFFFF)
        positions = struct.unpack("<%dI" % n_pos, pos_tbl)

        result = BytesIO()
        left = block.size
        for i in range(len(positions) - (2 if crc else 1)):
            sector = raw[positions[i]:positions[i + 1]]
            if key is not None:
                sector = self._decrypt(sector, (key + i) & 0xFFFFFFFF)
            if block.flags & MPQ_FILE_COMPRESS and left > len(sector):
                sector = _decompress(sector)
            left -= len(sector)
            result.write(sector)
        return result.getvalue()

    # --- public interface -------------------------------------------------
    def files(self) -> List[str]:
        entry = self._entry("(listfile)")
        if entry is not None:
            blob = self._read_block(
                "(listfile)", self._mpq.block_table[entry.block_table_index]
            ) or b""
            names = []
            for line in blob.decode("latin-1").replace("\r\n", "\n").split("\n"):
                name = line.strip()
                if name and not name.startswith("("):
                    names.append(name)
            if names:
                return sorted(names)
        # No (listfile): probe known client-patch DBC names by hash. WoW client
        # patches often ship without one, so this keeps them inspectable.
        return sorted(n for n in _KNOWN_NAMES if self._entry(n) is not None)

    def read(self, name: str) -> bytes:
        entry = self._entry(name)
        if entry is None:
            raise KeyError(name)
        block = self._mpq.block_table[entry.block_table_index]
        data = self._read_block(name, block)
        if data is None:
            raise KeyError(name)
        return data

    def _entry(self, name: str):
        return self._mpq.get_hash_table_entry(name)


def open_archive(path: str) -> Archive:
    return Archive(path)
