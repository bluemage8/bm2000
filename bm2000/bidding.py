"""Auction (bidding) model.

Supports parsing a simple bracketed bid list, e.g.::

    [1c, -p, 1h, -p, ...]     (dash = pass)
    1c, pass, 1h, pass, ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

SUITS = ["c", "d", "h", "s"]
NOTRUMP = "n"
LEVEL_CHARS = "1234567"
BID_RE = re.compile(r"^([1-7])([cdhsn])$")
SUIT_RANK = { "c": 0, "d": 1, "h": 2, "s": 3, "n": 4 }


@dataclass
class Bid:
    level: int
    suit: str  # 'c','d','h','s','n'  (n = notrump)
    is_double: bool = False
    is_redouble: bool = False

    @property
    def display(self) -> str:
        if self.is_redouble:
            return "RD"
        if self.is_double:
            return "Dbl"
        if self.suit == "n":
            return "%dNT" % self.level
        return "%d%s" % (self.level, self.suit.upper())


def parse_bid(token: str) -> Bid:
    token = token.strip().lower().replace("nt", "n").replace("pass", "p").replace("pass", "p")
    if token in ("p", "", "-"):
        return Bid(0, "-")
    if token in ("dbl", "x"):
        return Bid(0, "-", is_double=True)
    if token in ("rd", "xx"):
        return Bid(0, "-", is_redouble=True)
    m = BID_RE.match(token)
    if not m:
        raise ValueError("bad bid %r" % token)
    return Bid(int(m.group(1)), m.group(2))


def parse_auction(text: str) -> List[Bid]:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    tokens = [t.strip() for t in re.split(r"[,\s]+", text) if t.strip()]
    return [parse_bid(t) for t in tokens]


def bid_greater(a: Bid, b: Bid) -> bool:
    """True if bid a outranks bid b (standard bridge ranking)."""
    if a.is_double or a.is_redouble or a.suit == "-":
        return False
    if b.is_double or b.is_redouble or b.suit == "-":
        return True
    if a.level != b.level:
        return a.level > b.level
    return SUIT_RANK[a.suit] > SUIT_RANK[b.suit]


def final_contract(bids: List[Bid]):
    """Return (declarer_seat, level, suit) for the auction, or None.

    The declarer is the seat that made the highest (final) bid.
    """
    if not bids:
        return None
    top: Optional[Bid] = None
    top_i = -1
    for i, b in enumerate(bids):
        if b.suit == "-":
            continue
        if top is None or bid_greater(b, top):
            top = b
            top_i = i
    if top is None or top_i < 0:
        return None
    return top_i % 4, top.level, top.suit


def opening_hand_score(hand) -> int:
    """Simple HCP + long-suit points heuristic (for AI bidding stub)."""
    hcp = 0
    lengths = {s: 0 for s in range(4)}
    for c in hand:
        lengths[c.suit] += 1
        if c.rank == 14:
            hcp += 4
        elif c.rank == 13:
            hcp += 3
        elif c.rank == 12:
            hcp += 2
        elif c.rank == 11:
            hcp += 1
    openers = 0
    for s in range(4):
        if lengths[s] >= 5:
            openers += (lengths[s] - 3)
        elif lengths[s] == 4:
            openers += 0
    return hcp + openers
