"""Contract semantics: required tricks, game / slam detection, and scoring.

Bridge contract rules (the part the original teaching app got *implicitly*
right but our engines had wrong):

* A contract is **level + (trump suit | notrump)**, level 1..7.
* The **number of tricks the declarer side must take** is ``level + 6``
  (a 1-level contract needs 7 tricks, a 4-level high-major needs 10, a 7-level
  grand slam needs all 13).  Our older code compared the trick total against
  the bare ``level`` -- off by 6 -- which mis-judged every hand.
* **Game** (成局): a contract whose trick-score reaches the game line
  (100 trick points): 3NT, 4H/4S (120), or 5C/5D (100).  Levels 6/7 are
  slams.
* **Slam** (满贯): level 6 = small slam (小满贯), level 7 = grand slam
  (大满贯); each earns a slam bonus on top of the trick score.

``score_contract`` returns a breakdown so the UI can show the result the way a
bridge scorepad does (trick points, game/slam bonus, total, made/defeated).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# contract = (declarer_seat, level, suit); suit in {"c","d","h","s","n"} (n=NT)
NOTRUMP = "n"

# trick points per level for a *suit* contract (minors 20, majors 30)
_SUIT_POINTS = {"c": 20, "d": 20, "h": 30, "s": 30}
_NT_POINTS = 40  # first level NT = 40, each further level = 30

# slam / game bonuses (rubber bridge, non-vulnerable base values)
_GAME_BONUS = 300
_SMALL_SLAM_BONUS = 500
_GRAND_SLAM_BONUS = 750
_UNDERTRICK_PENALTY = 50  # per trick short (non-vulnerable, simplified)


@dataclass
class ContractInfo:
    level: int
    suit: str          # 'c' 'd' 'h' 's' 'n'
    declarer: int      # seat 0..3 that made the final bid
    dummy: int         # declarer's partner
    defense: Tuple[int, int]  # the two opposing seats

    @property
    def is_notrump(self) -> bool:
        return self.suit == NOTRUMP

    @property
    def text(self) -> str:
        return "%d%s" % (self.level, "NT" if self.is_notrump else self.suit.upper())

    @property
    def tricks_needed(self) -> int:
        """Tricks the declarer side must take: level + 6."""
        return self.level + 6

    @property
    def is_game(self) -> bool:
        """A making-contract line worth the game bonus (3NT, 4M, 5m)."""
        if self.is_notrump:
            return self.level >= 3
        if self.suit in ("h", "s"):
            return self.level >= 4
        return self.level >= 5   # minors need 5 for game

    @property
    def is_swing(self) -> bool:
        return self.level in (6, 7)

    @property
    def is_small_slam(self) -> bool:
        return self.level == 6

    @property
    def is_grand_slam(self) -> bool:
        return self.level == 7


def make_info(contract: Optional[Tuple[int, int, str]]) -> Optional[ContractInfo]:
    """Build a ContractInfo from the (declarer, level, suit) tuple, or None."""
    if not contract:
        return None
    declarer, level, suit = contract
    if suit not in ("c", "d", "h", "s", NOTRUMP) or not (1 <= level <= 7):
        return None
    dummy = (declarer + 2) % 4
    defense = tuple((declarer + 1 + k) % 4 for k in (0, 1))
    return ContractInfo(level=level, suit=suit, declarer=declarer, dummy=dummy,
                        defense=defense)


def trick_points(level: int, suit: str) -> int:
    """Trick score for a *made* contract (before game/slam bonuses)."""
    if suit == NOTRUMP:
        return 40 + 30 * (level - 1)
    return _SUIT_POINTS[suit] * level


def score_contract(won: int, contract: Optional[Tuple[int, int, str]]) -> dict:
    """Full score breakdown for a finished deal.

    Returns a dict the UI can render:
        {
          "text": "3NT", "level": 3, "suit": "n",
          "needed": 9, "won": 11,
          "made": True,            # won >= level + 6
          "over": 2,               # tricks over contract (>=0 when made)
          "under": 0,              # tricks short (>=0 when defeated)
          "trick_points": 100,     # 0 when defeated
          "bonus": 300,            # game / small-slam / grand-slam bonus
          "penalty": 0,            # undertrick penalty when defeated
          "total": 400,            # trick_points + bonus - penalty
          "kind": "game",          # "pass"|"minor"|"major"|"game"|"small_slam"|"grand_slam"
          "declarer": 0, "dummy": 2, "defense": (1, 3),
        }
    """
    info = make_info(contract)
    if info is None:
        return {
            "text": "Pass", "level": 0, "suit": "-", "needed": 0, "won": won,
            "made": False, "over": 0, "under": 0,
            "trick_points": 0, "bonus": 0, "penalty": 0, "total": 0,
            "kind": "pass",
            "declarer": -1, "dummy": -1, "defense": (-1, -1),
        }
    needed = info.tricks_needed
    made = won >= needed
    over = max(0, won - needed)
    under = max(0, needed - won)

    if made:
        tp = trick_points(info.level, info.suit)
        if info.is_grand_slam:
            bonus = _GRAND_SLAM_BONUS
            kind = "grand_slam"
        elif info.is_small_slam:
            bonus = _SMALL_SLAM_BONUS
            kind = "small_slam"
        elif info.is_game:
            bonus = _GAME_BONUS
            kind = "game"
        elif info.suit in ("h", "s"):
            bonus, kind = 0, "major"
        elif info.is_notrump:
            bonus, kind = 0, "nt"
        else:
            bonus, kind = 0, "minor"
        penalty = 0
        total = tp + bonus
    else:
        tp = 0
        bonus = 0
        penalty = under * _UNDERTRICK_PENALTY
        total = -penalty
        kind = "defeated"

    return {
        "text": info.text, "level": info.level, "suit": info.suit,
        "needed": needed, "won": won,
        "made": made, "over": over, "under": under,
        "trick_points": tp, "bonus": bonus, "penalty": penalty, "total": total,
        "kind": kind,
        "declarer": info.declarer, "dummy": info.dummy, "defense": info.defense,
    }
