"""Parser for the Bridge Master 2000 teaching script.

Each deal record in the ``Data`` blob is a token stream using ``|`` and CRLF
as field separators.  A record holds:

* ``md|...``  - the four hands (comma-separated, one hand per seat).
* ``mb|<bid>`` - a single bid in turn (``p`` = pass).  The auction is the
  sequence of ``mb`` values.
* ``cb| cg| cr|`` - contract-book codes (constant markers; the real contract
  is derived from the auction).
* ``pg``     - a "play group" marker.
* ``hs/<ls> <hc>/<lc> <pc>`` - animation frames.  ``hs`` = highlight-show,
  ``lc`` = low-clear, ``hc`` = high-clear, ``ls`` = low-show, ``pc`` =
  play-card.
* ``at| / nt|`` - narration caption text (human-readable teaching).

The play section is a *compressed, stateful* animation: a bare suit letter
(e.g. ``pc|s``) means "play the next card of that suit", and explicit tokens
(e.g. ``pc|sq``) name a specific card.  Because faithfully decoding which
physical card a bare letter refers to requires replaying full trick state
that the original app maintains internally, we capture the *steps* as
( kind, payload ) rather than a fixed card.  The GUI replays them by
following the deal + narration; the narration is the authoritative teaching
content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .bidding import Bid, final_contract, parse_bid
from .cards import Card, Deal, parse_md, validate_deal

# The real command vocabulary.  Everything else that appears is a *value*:
#   - seat-suit layout tokens  (sc, nc, sh, nh, ws, es, ...)
#   - card-group tokens        (dak, sak, hqj, dqj, cak, ...)
#   - bare card letters        (s, d, h, c)  and pass (p)
#   - undo (up), misc (y, r, sv, pn)
COMMANDS = {
    "st", "nt", "sk", "md", "mb", "cb", "cg", "cr", "wt", "up",
    "hc", "lc", "hs", "ls", "pc", "at",
    "pg",
}
CARD_TOKEN_RE = re.compile(r"^[sdhc][akqjt0-9]*$", re.IGNORECASE)
SEAT_SUIT_RE = re.compile(r"^[sdhc][sdhc]$", re.IGNORECASE)


# seat letter -> seat id
_SEAT_L = {"s": 0, "w": 1, "n": 2, "e": 3}


def step_seat_suit(payload: str):
    """Decode a seat-suit layout payload like 'sc' -> (seat, suit) or None."""
    if not payload or len(payload) != 2:
        return None
    a, b = payload[0].lower(), payload[1].lower()
    if a in _SEAT_L and b in "cdhs":
        return _SEAT_L[a], {"c": 0, "d": 1, "h": 2, "s": 3}[b]
    return None


@dataclass
class Step:
    kind: str  # 'layout' | 'play' | 'caption' | 'group'
    # layout: payload = 'show'/'hide'; seat_suit = (seat, suit)
    # play  : payload = card token ('', 's', 'sq', 'c6'...)
    # caption: payload = text
    cmd: str = ""
    payload: object = None
    seat: Optional[int] = None
    suit: Optional[int] = None


@dataclass
class Solution:
    deal: Optional[Deal]
    auction: List[Tuple[int, Optional[Bid]]] = field(default_factory=list)
    contract: Optional[Tuple[int, int, str]] = None
    vuln: str = ""
    steps: List[Step] = field(default_factory=list)
    names: List[str] = field(default_factory=list)

    @property
    def captions(self) -> List[str]:
        return [str(s.payload) for s in self.steps if s.kind == "caption"]


def _is_card_token(tok: str) -> bool:
    return bool(tok) and bool(CARD_TOKEN_RE.match(tok))


def _card_from_token(tok: str, default_rank: int = 11) -> Card:
    suit = {"c": 0, "d": 1, "h": 2, "s": 3}[tok[0].lower()]
    rest = tok[1:]
    rmap = {"a": 14, "k": 13, "q": 12, "j": 11, "t": 10, "0": 10}
    if rest:
        rank = rmap.get(rest[-1], int(rest[-1]) if rest[-1].isdigit() else default_rank)
    else:
        rank = default_rank
    return Card(rank, suit)


def parse_solution(rec: str) -> Solution:
    sol = Solution(deal=None)
    pieces = re.split(r"[\|\r\n]+", rec)
    i, n = 0, len(pieces)

    def consume_value(start: int) -> Tuple[str, int]:
        buf, j = [], start
        while j < n:
            p = pieces[j].strip()
            if p in COMMANDS:
                break
            buf.append(p)
            j += 1
        return " ".join(buf), j

    seat = 0
    while i < n:
        p = pieces[i].strip()
        if not p:
            i += 1
            continue
        if p in COMMANDS:
            if p == "md":
                val, i = consume_value(i + 1)
                if val:
                    try:
                        sol.deal = parse_md(val)
                    except ValueError:
                        pass
                continue
            if p == "mb":
                val, i = consume_value(i + 1)
                bid = None if val in ("", "p") else _safe_bid(val)
                sol.auction.append((seat % 4, bid))
                seat += 1
                continue
            if p in ("cb", "cr"):
                val, i = consume_value(i + 1)
                continue
            if p == "cg":
                val, i = consume_value(i + 1)
                sol.vuln = _vuln(val)
                continue
            if p == "pg":
                sol.steps.append(Step(kind="group"))
                i += 1
                continue
            if p in ("hs", "ls", "hc", "lc", "pc"):
                val, i = consume_value(i + 1)
                _emit(p, val, sol)
                continue
            if p in ("at", "nt"):
                val, i = consume_value(i + 1)
                if val:
                    sol.steps.append(Step(kind="caption", payload=val))
                continue
            i += 1
            continue
        i += 1

    nonp = [b for _s, b in sol.auction if b is not None]
    if nonp:
        sol.contract = final_contract(nonp)
    return sol


def _vuln(val: str) -> str:
    # '010' / '0200' style code - keep raw; display maps it in the GUI.
    return (val or "").strip()


def _safe_bid(val: str) -> Optional[Bid]:
    try:
        return parse_bid(val)
    except Exception:
        return None


def _emit(cmd: str, val: str, sol: Solution) -> None:
    if cmd == "pc":
        sol.steps.append(Step(kind="play", cmd=cmd, payload=val or ""))
    else:
        ss = step_seat_suit(val)
        show = cmd in ("hs", "hc")
        sol.steps.append(
            Step(
                kind="layout",
                cmd=cmd,
                payload="show" if show else "hide",
                seat=ss[0] if ss else None,
                suit=ss[1] if ss else None,
            )
        )


# Back-compat names used elsewhere
Frame = Step


@dataclass
class Script(Solution):
    frames: List[Step] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.frames = self.steps


def parse_script(rec: str) -> "Script":
    sol = parse_solution(rec)
    scr = Script(
        deal=sol.deal,
        auction=sol.auction,
        contract=sol.contract,
        vuln=sol.vuln,
        steps=sol.steps,
        names=list(sol.names),
    )
    scr.frames = scr.steps
    return scr
