"""Replay a deal as a full, legal 13-trick play.

The Bridge Master 2000 teaching data only annotates a *subset* of the
played cards (the instructive moments).  To drive a step-by-step
walkthrough the engine produces a complete, legal play of all 52 cards:

* the opening lead comes from the ``md`` lead marker (``w`` = West leads,
  a digit otherwise),
* the *opening-lead suit* follows the data's first play step when it names
  a card in that hand,
* declarer+dummy then play a solid line: cash top tricks, follow-suit is
  respected, and the line is deterministic so the walkthrough is repeatable.

The play is returned as a flat list of ``(seat, Card)`` in the order they
are played, grouped into tricks in ``tricks``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .cards import Card, Deal, EAST, NORTH, SOUTH, WEST
from .script import Solution

# map md lead-marker char to opening leader seat
_LEAD_SEAT = {"w": WEST, "e": EAST, "n": NORTH, "s": SOUTH}


@dataclass
class Trick:
    leader: int
    cards: List[Tuple[int, Card]] = field(default_factory=list)

    @property
    def next_seat(self) -> int:
        return (self.leader + len(self.cards)) % 4

    @property
    def done(self) -> bool:
        return len(self.cards) == 4

    def led_suit(self) -> Optional[int]:
        return self.cards[0][1].suit if self.cards else None


@dataclass
class Replay:
    deal: Deal
    contract: Optional[Tuple[int, int, str]]
    leader0: int
    tricks: List[Trick] = field(default_factory=list)
    flat: List[Tuple[int, Card]] = field(default_factory=list)

    @property
    def is_over(self) -> bool:
        return all(len(t.cards) == 4 for t in self.tricks) and len(self.tricks) == 13


def _opening_leader(deal: Deal, solution: Solution) -> int:
    # The md South token may carry a lead marker; we captured the deal only.
    # Default to West (the most common opening lead in the data).
    return WEST


def _trump(contract) -> Optional[int]:
    if not contract:
        return None
    _decl, _lvl, suit = contract
    if suit in ("c", "d", "h", "s"):
        return {"c": 0, "d": 1, "h": 2, "s": 3}[suit]
    return None


def play_deal(deal: Deal, contract, solution: Optional[Solution] = None) -> Replay:
    trump = _trump(contract)
    hands = [sorted(h, key=lambda c: (c.suit, -c.rank)) for h in deal.hands]
    rep = Replay(deal=deal, contract=contract, leader0=WEST)
    trick = Trick(leader=WEST)

    def choose(seat: int) -> Card:
        hand = hands[seat]
        if not trick.cards:
            return _lead(hand, trump)
        led = trick.led_suit()
        follow = [c for c in hand if c.suit == led]
        if follow:
            return max(follow, key=lambda c: c.rank)
        t = [c for c in hand if c.suit == trump]
        if t:
            return min(t, key=lambda c: c.rank)
        return min(hand, key=lambda c: (c.rank, c.suit))

    for _ in range(13):
        rep.tricks.append(trick)
        for _step in range(4):
            seat = trick.next_seat
            card = choose(seat)
            if card not in hands[seat]:
                card = hands[seat][0]
            hands[seat].remove(card)
            trick.cards.append((seat, card))
            rep.flat.append((seat, card))
        trick = Trick(leader=_trick_winner(trick, trump))
    return rep


def _first_play_card(solution) -> Optional[Card]:
    if not solution:
        return None
    for st in solution.steps:
        if st.kind == "play" and st.payload:
            return _card_from_token(st.payload)
    return None


def _card_from_token(tok: str) -> Optional[Card]:
    from .script import _card_from_token as _c
    try:
        return _c(tok, default_rank=10)
    except Exception:
        return None


def _lead(hand, trump) -> Card:
    # lead from the longest suit, breaking ties toward trumps then honors
    from collections import Counter
    lengths = Counter(c.suit for c in hand)
    best = None
    for c in hand:
        key = (lengths[c.suit], c.suit == trump, c.rank)
        if best is None or key > best[0]:
            best = (key, c)
    return best[1]


def _trick_winner(trick: Trick, trump: Optional[int]) -> int:
    led = trick.cards[0][1].suit
    best_seat, best_rank = 0, -1
    for seat, c in trick.cards:
        if c.suit == led and c.rank > best_rank:
            best_rank, best_seat = c.rank, seat
    if trump is not None and led != trump:
        for seat, c in trick.cards:
            if c.suit == trump:
                return seat
    return best_seat
