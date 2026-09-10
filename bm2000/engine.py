"""A lightweight declarer (South) engine for the Bridge Master 2000
re-implementation.

Features:
* follow-suit / must-follow enforcement
* trick win detection (highest of the led suit; a trump wins if none follows)
* a simple but not-trivial AI (``AI``) that leads by suit length and HCP,
  follows with the highest card, and discards from long suits
* contract scoring (``score_contract`` / ``contract_result``)

This is intentionally not a full bridge solver; it exists so the deals are
playable and the results are plausible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cards import SUIT_NAMES, Card


class Trick:
    def __init__(self, leader: int) -> None:
        self.leader = leader
        self.cards: List[Tuple[int, object]] = []

    @property
    def played_count(self) -> int:
        return len(self.cards)

    @property
    def next_seat(self) -> int:
        return (self.leader + self.played_count) % 4

    @property
    def done(self) -> bool:
        return self.played_count == 4

    def led_suit(self) -> Optional[int]:
        return self.cards[0][1].suit if self.cards else None


@dataclass
class Board:
    hands: List[List[object]] = field(default_factory=list)
    trump: Optional[int] = None
    contract: Optional[Tuple[int, int, str]] = None
    leading: int = 0
    trick: Trick = field(default_factory=lambda: Trick(0))
    history: List[List[Tuple[int, object]]] = field(default_factory=list)
    last_winner: Optional[int] = None

    _initial: Optional[List[List[object]]] = field(default=None, repr=False)

    @classmethod
    def from_deal(cls, deal, contract: Optional[Tuple[int, int, str]] = None) -> "Board":
        hands = [sorted(h, key=lambda c: (c.suit, -c.rank)) for h in deal.hands]
        board = cls(hands=hands)
        board._initial = [list(h) for h in hands]
        if contract is not None:
            board.contract = contract
            _decl, _lvl, suit = contract
            suit_name = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}.get(suit)
            board.trump = SUIT_NAMES.index(suit_name) if suit_name else None
        return board

    def valid_cards(self, seat: int) -> List[object]:
        hand = self.hands[seat]
        if not self.trick.cards:
            return list(hand)
        led = self.trick.led_suit()
        follow = [c for c in hand if c.suit == led]
        return follow if follow else list(hand)

    @property
    def turn(self) -> int:
        return self.leading if not self.trick.cards else self.trick.next_seat

    def is_over(self) -> bool:
        return all(len(h) == 0 for h in self.hands)

    def play(self, seat: int, card) -> int:
        if seat != self.turn:
            raise AssertionError("not seat %d's turn (expected %d)" % (seat, self.turn))
        hand = self.hands[seat]
        if card not in hand:
            raise AssertionError("card %r not in hand" % card)
        hand.remove(card)
        self.trick.cards.append((seat, card))
        if self.trick.done:
            winner = self._trick_winner()
            self.history.append(list(self.trick.cards))
            self.last_winner = winner
            self.leading = winner
            self.trick = Trick(leader=winner)
            return winner
        return -1

    def _trick_winner(self) -> int:
        cards = self.trick.cards
        led = cards[0][1].suit
        best_seat, best_rank = None, -1
        for seat, c in cards:
            if c.suit == led and c.rank > best_rank:
                best_rank, best_seat = c.rank, seat
        if not cards:
            return self.leading
        if self.trump is not None and led != self.trump:
            for seat, c in cards:
                if c.suit == self.trump:
                    return seat
        return best_seat

    def reset(self, contract=None) -> None:
        initial = self._initial if self._initial is not None else [list(h) for h in self.hands]
        if contract is not None:
            self.contract = contract
            _d, _l, suit = contract
            suit_name = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}.get(suit)
            self.trump = SUIT_NAMES.index(suit_name) if suit_name else None
        self.hands = [list(h) for h in initial]
        self.leading, self.trick, self.history, self.last_winner = 0, Trick(0), [], None


_HCP = {14: 4, 13: 3, 12: 2, 11: 1}


def _hcp(hand) -> int:
    return sum(_HCP.get(c.rank, 0) for c in hand)


class AI:
    """A simple AI.

    * Leading: play a card from the longest suit; weight high cards so
      you lead strength but keep low cards for discards later.
    * Following: play the highest card of the led suit (take the trick if
      you can, otherwise shed a card).  If short, discard from the longest
      non-trump suit.
    """

    def choose(self, board: Board, seat: int):
        valid = board.valid_cards(seat)
        if not valid:
            raise ValueError("no valid card for seat %d" % seat)
        lengths: Dict[int, int] = {}
        for c in valid:
            lengths[c.suit] = lengths.get(c.suit, 0) + 1
        if not board.trick.cards:
            # lead from the longest suit that also contains some strength;
            # play the highest card of that suit (lead with strength).
            top_suit = max(lengths, key=lambda s: (lengths[s], _hcp([c for c in valid if c.suit == s])))
            cand = sorted((c for c in valid if c.suit == top_suit), key=lambda c: -c.rank)
            return cand[0]
        led = board.trick.led_suit()
        follow = sorted((c for c in valid if c.suit == led), key=lambda c: -c.rank)
        if follow:
            return follow[0]
        # discard: longest non-trump, lowest card
        non_trump = [s for s in lengths if s != board.trump]
        pool = non_trump or list(lengths)
        pool.sort(key=lambda s: -lengths[s])
        return min((c for c in valid if c.suit in pool), key=lambda c: (c.rank, c.suit))


# back-compat alias
DeclarerAI = AI


def score_contract(board: "Board", declarer: int) -> Tuple[int, int]:
    """Return (tricks_won_by_declarer_side, level)."""
    partner = (declarer + 2) % 4
    side = {declarer, partner}
    won = sum(1 for trick in board.history if trick[0][0] in side)
    level = board.contract[1] if board.contract else 0
    return won, level


def contract_result(won: int, level: int) -> int:
    """Signed result: positive = makes, negative = number of tricks short."""
    return won - level
