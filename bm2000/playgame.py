"""Interactive trick-by-trick play engine for the Bridge Master 2000 rework.

Faithful to the original's teaching model (see analysis/SPEC_orig.md and the
help file, "About Bridge Master's play"):

  * The human plays BOTH South (declarer) and North (dummy).
  * The computer plays East and West, the defense.
  * The defense's one objective is to defeat the contract.  It plays its own
    cards automatically using standard defensive conventions:
        - on the opening lead: fourth best from 4+, high from a doubleton,
          low from a 3-card holding with no honor sequence;
        - it follows suit when possible; it ruffs with a trump when it
          reasonably can; it tries to take tricks / cut the declarer's
          communications.
  * The declarer may play ANY legal card (follow suit, else ruff or discard).
  * The contract is made only if the declarer's side (N+S) takes at least the
    number of tricks demanded.

The engine is a plain state machine (no GUI dependency) so it can be unit
tested.  It records every trick so the GUI can render the board and replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .cards import Card, Deal, EAST, NORTH, SOUTH, WEST  # noqa: E402

SOUTH_N = (SOUTH, NORTH)            # the human (declarer + dummy)
EAST_W = (EAST, WEST)               # the computer defense


def trump_of(contract) -> Optional[int]:
    if not contract:
        return None
    _d, _lvl, suit = contract
    if suit in ("c", "d", "h", "s"):
        return {"c": 0, "d": 1, "h": 2, "s": 3}[suit]
    return None


def trick_winner(trick: List[Tuple[int, Card]], trump: Optional[int]) -> int:
    led = trick[0][1].suit
    best_seat, best_rank = trick[0][0], trick[0][1].rank
    trump_plays = []
    for seat, c in trick:
        if c.suit == trump:
            trump_plays.append((seat, c.rank))
    if trump_plays and led != trump:
        # the highest trump wins the trick
        seat, _r = max(trump_plays, key=lambda t: t[1])
        return seat
    for seat, c in trick:
        if c.suit == led and c.rank > best_rank:
            best_rank, best_seat = c.rank, seat
    return best_seat


def side_of(seat: int) -> int:
    """0 = NS (declarer), 1 = EW (defense)."""
    return 0 if seat in SOUTH_N else 1


def legal_cards(hand: List[Card], trick: List[Tuple[int, Card]]) -> List[Card]:
    if not trick:
        return list(hand)
    led = trick[0][1].suit
    follow = [c for c in hand if c.suit == led]
    return follow if follow else list(hand)


# --- defensive opening-lead convention -------------------------------------- #
def _opening_lead(hand: List[Card], trump: Optional[int]) -> Card:
    if not hand:
        raise ValueError("empty hand")
    # longest suit first; if no trump, lead the longest suit's 4th best;
    # honors (A/K/Q/J) are led high from sequences.
    suits = {}
    for c in hand:
        suits.setdefault(c.suit, []).append(c)
    for ls in suits.values():
        ls.sort(key=lambda c: c.rank)  # ascending

    def score(suit: List[Card]) -> tuple:
        n = len(suit)
        # prefer 4+ card suits, avoid leading into a void of trumps
        top3 = [c.rank for c in suit[-3:]]
        seq = 1
        for a, b in zip(top3, top3[1:]):
            if b == a + 1:
                seq += 1
        return (n >= 4, n, seq, -suit[0].rank)

    best_suit = max(suits.values(), key=score)
    n = len(best_suit)
    if n == 2:
        return best_suit[-1]          # high from a doubleton
    if n == 3:
        return best_suit[0]           # low from a 3-card without sequence
    # 4+ : fourth best (or low from a long suit)
    return best_suit[-4] if n >= 4 else best_suit[0]


# --- defensive follow-to-trick logic ---------------------------------------- #
def _defense_follow(seat: int, hand: List[Card], trick: List[Tuple[int, Card]],
                    trump: Optional[int], tricks_taken_ew: int,
                    total_tricks: int) -> Card:
    if not trick:
        return _opening_lead(hand, trump)
    led = trick[0][1].suit
    follow = [c for c in hand if c.suit == led]
    trump_hand = [c for c in hand if c.suit == trump]

    # 1) Must follow suit when able.  Play low, unless we can win the trick.
    if follow:
        # if a higher led-suit card already played, our follow can't win -> low
        max_led_played = max((c.rank for _s, c in trick if c.suit == led),
                             default=0)
        winners = [c for c in follow if c.rank > max_led_played
                   and led == trump]  # only a led-suit win counts vs. trump
        if winners:
            return min(winners, key=lambda c: c.rank)
        return min(follow, key=lambda c: c.rank)

    # 2) Void in the led suit: ruff when possible (smallest trump that seems
    #    useful), and only when it isn't the lead suit.
    if trump is not None and led != trump and trump_hand:
        highest_trump_played = max((c.rank for _s, c in trick if c.suit == trump),
                                   default=None)
        if highest_trump_played is None:
            return min(trump_hand, key=lambda c: c.rank)

    # 3) Discard the least useful card (small trump, else small spot).
    if trump is not None and trump_hand:
        return min(trump_hand, key=lambda c: c.rank)
    return min(hand, key=lambda c: (c.rank, c.suit))


# --- the engine ------------------------------------------------------------- #
@dataclass
class PlayState:
    deal: Deal
    contract: Optional[Tuple[int, int, str]]
    hands: List[List[Card]]
    trump: Optional[int]
    leader: int
    trick: List[Tuple[int, Card]] = field(default_factory=list)
    tricks: List[List[Tuple[int, Card]]] = field(default_factory=list)
    won_ns: int = 0
    done: bool = False
    opened: bool = False

    # -- queries ------------------------------------------------------------ #
    @property
    def to_play(self) -> Optional[int]:
        if self.done:
            return None
        seat = (self.leader + len(self.trick)) % 4
        return seat

    @property
    def tricks_played(self) -> int:
        return len(self.tricks)

    def hand(self, seat: int) -> List[Card]:
        return self.hands[seat]

    def legal(self) -> List[Card]:
        seat = self.to_play
        if seat is None:
            return []
        return legal_cards(self.hands[seat], self.trick)

    def score(self) -> Tuple[int, int]:
        level = self.contract[1] if self.contract else 0
        return self.won_ns, level

    def made(self) -> bool:
        if not self.contract:
            return True
        return self.won_ns >= self.contract[1]

    # -- actions ------------------------------------------------------------ #
    def play(self, card: Card) -> Optional[int]:
        """Play `card` for the seat to move.  Returns the trick winner (or None
        while the trick is still open)."""
        if self.done or card not in self.legal():
            return None
        seat = self.to_play
        self.hands[seat].remove(card)
        self.trick.append((seat, card))
        if len(self.trick) == 4:
            winner = trick_winner(self.trick, self.trump)
            self.tricks.append(self.trick)
            if side_of(winner) == 0:
                self.won_ns += 1
            self.leader = winner
            self.trick = []
            if len(self.tricks) == 13:
                self.done = True
                return winner
            return winner
        return None

    def auto_defense_step(self) -> Optional[int]:
        """Let the defense (E/W) play one card.  Returns trick winner on close."""
        seat = self.to_play
        if seat is None or seat not in EAST_W:
            return None
        card = _defense_follow(seat, self.hands[seat], self.trick, self.trump,
                               13 - self.won_ns, 13 - self.tricks_played)
        return self.play(card)


def start(deal: Deal, contract: Optional[Tuple[int, int, str]]) -> PlayState:
    trump = trump_of(contract)
    hands = [sorted(h, key=lambda c: (c.suit, -c.rank)) for h in deal.hands]
    # opening leader: the defense leads on the declarer's left.  In our model the
    # human is NS, so the opening lead comes from West (West leads into dummy).
    leader = WEST
    state = PlayState(deal=deal, contract=contract, hands=hands, trump=trump,
                      leader=leader)
    return state
