"""Pluggable decoder registry.

Each decoder is an object with:
    matches(filename: str) -> bool
    render(filename: str, data: bytes) -> str | None      # Markdown, or None

To support a new file type inside an MPQ, add a module here that defines a
decoder and append an instance to DECODERS. The first decoder whose matches()
returns True and whose render() returns a non-None string wins. Anything left
over falls back to the generic file manifest in inspect.py.
"""
from .charbaseinfo import CharBaseInfoDecoder
from .charstartoutfit import CharStartOutfitDecoder
from .chartitles import CharTitlesDecoder
from .chrinfo import ChrClassesDecoder, ChrRacesDecoder
from .dbc import GenericDbcDecoder
from .skillraceclassinfo import SkillRaceClassInfoDecoder
from .text import TextDecoder

# Order matters: most specific first.
DECODERS = [
    CharBaseInfoDecoder(),          # CharBaseInfo.dbc -> race/class combo diff
    CharStartOutfitDecoder(),       # CharStartOutfit.dbc -> starting gear per combo
    SkillRaceClassInfoDecoder(),    # SkillRaceClassInfo.dbc -> weapon/armor grants
    ChrClassesDecoder(),            # ChrClasses.dbc -> class ids + names
    ChrRacesDecoder(),              # ChrRaces.dbc -> race ids + names
    CharTitlesDecoder(),            # CharTitles.dbc -> title ids + text
    GenericDbcDecoder(),            # any other *.dbc -> header stats
    TextDecoder(),                  # *.lua/*.xml/*.txt/*.toc -> text preview
]


def render_all(filename: str, data: bytes):
    """Return the first non-empty Markdown section for this file, or None."""
    for dec in DECODERS:
        try:
            if dec.matches(filename):
                out = dec.render(filename, data)
                if out:
                    return out
        except Exception as e:  # noqa: BLE001 - a bad decoder must not kill the run
            return f"> ⚠️ decoder `{type(dec).__name__}` failed on `{filename}`: `{e}`"
    return None
