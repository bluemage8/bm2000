"""Loading of the Bridge Master 2000 level / deal data.

On disk each level lives in ``winexe/hands/<n>/``:

* ``Data``  - a single text blob: a stream of records.  Every record
  starts with the marker ``st||nt||sk`` and holds one bridge deal
  (``md`` field), its vulnerability/contract (``cb``/``cg``/``cr``) and
  a teaching narration (``at``/``nt``/... animation steps).
* ``Index`` - a table of 12-byte entries (8-byte zero padded ``.LIN``
  filename + a 2-byte little-endian offset) intended as a fast lookup
  into ``Data``.  The offsets are compressed in a way the original
  binary resolves internally; rather than reproduce that scheme we scan
  the blob directly for record markers, which is exact and robust.

Records in the blob correspond one-to-one, in order, to the deals.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .cards import Deal, parse_md, validate_deal
from .script import Solution, parse_solution

_CMD_RE = re.compile(r"^[a-zA-Z!]{1,4}$")
_VALUE_CMDS = {"md", "cb", "cg", "cr"}
_START_RE = re.compile(rb"st\|\|nt\|\|sk")


@dataclass
class DealRecord:
    """One teachable deal (one record from the Data blob)."""

    name: str = "?"
    start: int = 0
    end: int = 0
    vuln: str = ""
    contract: str = ""
    note: str = ""
    deal: Optional[Deal] = None
    solution: Optional["Solution"] = None
    commands: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def has_deal(self) -> bool:
        return self.deal is not None and validate_deal(self.deal)

    @property
    def captions(self) -> List[str]:
        if self.solution:
            return self.solution.captions
        return [self.note] if self.note else []


def _clean(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _parse_record(text: str) -> DealRecord:
    rec = DealRecord()
    sol = parse_solution(text)
    rec.solution = sol
    rec.deal = sol.deal
    rec.vuln = sol.vuln
    if sol.contract is not None:
        rec.contract = "%d%s" % (sol.contract[1], sol.contract[2])
    cap = sol.captions
    rec.note = _clean(" ".join(cap))
    # Keep the raw command/value pairs for reference.
    rec.commands = []
    return rec


def find_record_spans(blob: bytes) -> List[Tuple[int, int]]:
    starts = [m.start() for m in _START_RE.finditer(blob)]
    spans = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(blob)
        spans.append((s, e))
    return spans


def _read_index_names(path: Path) -> List[str]:
    data = path.read_bytes()
    names: List[str] = []
    for off in range(0, len(data) - 12 + 1, 12):
        name = data[off : off + 8]
        if name.count(b"\x00") and name.rstrip(b"\x00").isdigit() == False:
            pass
        nm = name.split(b"\x00")[0].decode("ascii", "replace").strip()
        if nm and re.match(r"^[A-Z]+\d+\.(LIN|lin)$", nm):
            names.append(nm)
    return names


class Level:
    def __init__(self, number: int, base: Path) -> None:
        self.number = number
        self.base = base
        blob = (base / "Data").read_bytes()
        self.blob = blob
        starts = [m.start() for m in _START_RE.finditer(blob)]
        self.records: List[DealRecord] = []
        names = _read_index_names(base / "Index")
        for i, (s, e) in enumerate(find_record_spans(blob)):
            rec = _parse_record(blob[s:e].decode("latin1"))
            rec.start, rec.end = s, e
            if i < len(names):
                rec.name = names[i]
            else:
                rec.name = "%s%02d" % (self.series_letter, i + 1)
            self.records.append(rec)

    @property
    def series_letter(self) -> str:
        # Levels 1..5 use series letters A..E (matches the original data
        # series A/B/C/D/E).  Higher numbers would wrap with an alpha prefix.
        n = int(self.number)
        letter, rem = divmod(n - 1, 26)
        if letter == 0:
            return chr(ord("A") + rem)
        return chr(ord("A") + letter - 1) + chr(ord("A") + rem)

    def deal_count(self) -> int:
        return len(self.records)

    def valid_deal_count(self) -> int:
        return sum(1 for r in self.records if r.has_deal)

    def names(self) -> List[str]:
        return [r.name for r in self.records]

    def by_name(self, name: str) -> Optional[DealRecord]:
        for r in self.records:
            if r.name == name:
                return r
        return None


def load_level(number: int, winexe: Path) -> Level:
    base = winexe / "hands" / str(number)
    if not ((base / "Data").exists() and (base / "Index").exists()):
        raise FileNotFoundError("level %i not found under %s" % (number, base))
    return Level(number, base)


def load_all_levels(winexe: Path) -> List[Level]:
    hands = winexe / "hands"
    numbers = []
    if hands.exists():
        for p in hands.iterdir():
            if p.is_dir() and p.name.isdigit():
                numbers.append(int(p.name))
    numbers.sort()
    out: List[Level] = []
    for n in numbers:
        try:
            out.append(load_level(n, winexe))
        except Exception:
            pass
    return out
