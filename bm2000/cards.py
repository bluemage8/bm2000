"""Core bridge card / deal model.

The Bridge Master 2000 "md" (make deal) command encodes the four hands.
The value is a comma-separated list of four suits, one per seat
(South, West, North, East), and within each suit a run of ranks given
from highest to lowest (A > K > Q > J > T/0 > 9 > ... > 2).

Example md value (first deal, level 1, series A, deal 1):
    3SJ32HA32DK32CAQ32,skt987h9876dqjtct,SQ4HK54DA654CKJ54
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

SOUTH = 0
WEST = 1
NORTH = 2
EAST = 3
SEAT_NAMES = ["South", "West", "North", "East"]
SEAT_LETTERS = ["S", "W", "N", "E"]

# rank characters as seen in the data (both spellings) -> numeric rank
RANK_MAP = {
    "a": 14,
    "k": 13,
    "q": 12,
    "j": 11,
    "t": 10,
    "0": 10,
    "9": 9,
    "8": 8,
    "7": 7,
    "6": 6,
    "5": 5,
    "4": 4,
    "3": 3,
    "2": 2,
}
# numeric rank -> canonical rank string
RANK_CHARS = {
    14: "A",
    13: "K",
    12: "Q",
    11: "J",
    10: "T",
    9: "9",
    8: "8",
    7: "7",
    6: "6",
    5: "5",
    4: "4",
    3: "3",
    2: "2",
}

# suit letter (in md) -> suit id. 0=clubs 1=diamonds 2=hearts 3=spades
SUIT_MAP = {"c": 0, "d": 1, "h": 2, "s": 3}
SUIT_NAMES = ["Clubs", "Diamonds", "Hearts", "Spades"]
SUIT_ABBR = ["C", "D", "H", "S"]
# unicode suit symbols for display
SUIT_SYMBOL = {0: "\u2663", 1: "\u2666", 2: "\u2665", 3: "\u2660"}


class Card:
    __slots__ = ("rank", "suit")

    def __init__(self, rank: int, suit: int) -> None:
        self.rank = rank
        self.suit = suit

    def short(self) -> str:
        return RANK_CHARS[self.rank] + SUIT_ABBR[self.suit]

    @property
    def is_honor(self) -> bool:
        return self.rank >= 11

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Card) and self.rank == other.rank and self.suit == other.suit
        )

    def __hash__(self) -> int:
        return (self.rank, self.suit).__hash__()

    def __repr__(self) -> str:
        return "%s%s" % (RANK_CHARS[self.rank], SUIT_ABBR[self.suit])


@dataclass
class Deal:
    """A parsed bridge deal (the 52 cards split into four hands)."""

    hands: List[List[Card]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.hands) != 4:
            self.hands = [[] for _ in range(4)]

    def seat(self, seat: int) -> List[Card]:
        return self.hands[seat]

    def sorted_hands(self) -> List[List[Card]]:
        return [sorted(h, key=lambda c: (c.suit, -c.rank)) for h in self.hands]

    def hcp(self, seat: int) -> int:
        total = 0
        for c in self.hands[seat]:
            if c.rank == 14:
                total += 4
            elif c.rank == 13:
                total += 3
            elif c.rank == 12:
                total += 2
            elif c.rank == 11:
                total += 1
        return total

    def hand_str(self, seat: int) -> str:
        out = []
        for s in range(4):
            cs = [c for c in self.hands[seat] if c.suit == s]
            if cs:
                cs.sort(key=lambda c: -c.rank)
                out.append(SUIT_SYMBOL[s] + "".join(RANK_CHARS[c.rank] for c in cs))
        return "  ".join(out)

    def all_cards(self) -> List[Card]:
        return [c for h in self.hands for c in h]


def _split_suit_tokens(md_value: str) -> List[str]:
    """Split the md value into its comma-separated tokens."""
    return md_value.split(",")


def parse_md(md_value: str) -> Deal:
    """Parse a bridge deal from the "md" command value.

    Accepts either the compact four-token form used by the Bridge Master
    data files, or any comma-separated list of four suit strings.
    """
    tokens = md_value.split(",")
    if len(tokens) == 4:
        return _parse_4_field(tokens)
    if len(tokens) == 3:
        return _parse_3_field(tokens)
    raise ValueError("md value must have 3 or 4 comma-separated tokens: %r" % md_value)


def _parse_3_field(tokens) -> "Deal":
    """lead,south,west,north  --  East is the complement (hidden hand)."""
    s_tok = tokens[0]
    # Drop a single leading digit/marker that is not followed by a rank
    # (e.g. '3SJ32...' -> lead marker '3', hand 'SJ32...').
    s_tok = _strip_lead_marker(s_tok)
    deal = Deal(hands=[[] for _ in range(4)])
    _parse_suit_str(deal, SOUTH, s_tok)
    _parse_suit_str(deal, WEST, tokens[1])
    _parse_suit_str(deal, NORTH, tokens[2])
    # East = whatever is missing
    deal.hands[EAST] = _complement_hand(deal)
    return deal


def _parse_4_field(tokens) -> "Deal":
    deal = Deal(hands=[[] for _ in range(4)])
    for seat, token in [(SOUTH, tokens[0]), (WEST, tokens[1]),
                         (NORTH, tokens[2]), (EAST, tokens[3])]:
        if token:
            _parse_suit_str(deal, seat, _strip_lead_marker(token))
    return deal


def _strip_lead_marker(token: str) -> str:
    """Drop a leading lead-marker from a South-hand token.

    A marker is a single non-suit char (a digit like ``3`` or a letter
    like ``w``) immediately followed by a suit letter.  A real hand run
    never has a non-suit char directly before a suit letter (suits
    always start a run), so this is unambiguous.
    """
    if len(token) > 1 and token[0].lower() not in "cdhs" and token[1].lower() in "cdhs":
        return token[1:]
    return token


def _complement_hand(deal: "Deal") -> List[Card]:
    present = set()
    for h in deal.hands:
        for c in h:
            present.add((c.suit, c.rank))
    out: List[Card] = []
    for s in range(4):
        for r in range(2, 15):
            if (s, r) not in present:
                out.append(Card(r, s))
    return out


def _parse_suit_str(deal: Deal, seat: int, token: str) -> None:
    current_suit = None
    for ch in token:
        low = ch.lower()
        if low in SUIT_MAP:
            current_suit = SUIT_MAP[low]
        elif low in RANK_MAP and current_suit is not None:
            deal.hands[seat].append(Card(RANK_MAP[low], current_suit))
        else:
            raise ValueError("bad char %r in md token %r" % (ch, token))


def _parse_lead(deal: Deal, lead: str) -> None:
    """Attach the opening-lead card to the seat it belongs to.

    The lead format is ``<level><suit><rank>`` e.g. ``3S`` (a spade
    led, with the 3 denoting trick-level), or a plain card like ``h8``.
    We simply parse the rank+suit and add to the seat that currently
    holds the card (matching by suit/rank); if not found, add to South.
    """
    lead = lead.strip()
    if not lead:
        return
    current_suit = None
    ranks: List[int] = []
    for ch in lead:
        low = ch.lower()
        if low in SUIT_MAP:
            if current_suit is None:
                current_suit = SUIT_MAP[low]
        elif low in RANK_MAP:
            ranks.append(RANK_MAP[low])
    if current_suit is None or not ranks:
        return
    card = Card(ranks[-1], current_suit)
    for seat in range(4):
        if card in deal.hands[seat]:
            return
    deal.hands[SOUTH].append(card)


def validate_deal(deal: Deal) -> bool:
    ranks_by_suit = {s: set() for s in range(4)}
    for h in deal.hands:
        for c in h:
            if c.rank in ranks_by_suit[c.suit]:
                return False
            ranks_by_suit[c.suit].add(c.rank)
    return all(len(r) == 13 for r in ranks_by_suit.values()) and len(deal.all_cards()) == 52


def encode_md(deal: Deal) -> str:
    """Inverse of parse_md: produce the compact md value for a deal."""
    seat_parts = []
    for seat in range(4):
        suit_bits = []
        for s in range(4):
            cs = [c for c in deal.hands[seat] if c.suit == s]
            if cs:
                cs.sort(key=lambda c: -c.rank)
                suit_bits.append(SUIT_ABBR[s].lower() + "".join(RANK_CHARS[c.rank] for c in cs))
        seat_parts.append("".join(suit_bits))
    return ",".join(seat_parts)


def parse_md_value(md_value: str) -> Deal:
    """Parse the raw md field value (a string after the 'md|' token)."""
    # strip stray line breaks / whitespace that may be embedded
    value = " ".join(md_value.split())
    return parse_md(value)
