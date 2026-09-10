"""Generate web/deals.json from the Bridge Master 2000 data.

Reuses the tested Python parse pipeline (levels.load_all_levels + script.
parse_solution) so the web app plays exactly the same 537 deals, contracts and
narration as the desktop build.  The JSON shape is consumed by web/app.js.

Run:  py web/gen_deals.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bm2000.levels import load_all_levels  # noqa: E402
from bm2000.cards import validate_deal  # noqa: E402

RANK_CHARS = {14: "A", 13: "K", 12: "Q", 11: "J", 10: "T", 9: "9",
              8: "8", 7: "7", 6: "6", 5: "5", 4: "4", 3: "3", 2: "2"}
SUIT_ABBR = ["c", "d", "h", "s"]


def hand_to_cards(hand) -> list:
    """Serialize one seat's 13 cards as {cards:[{r,r,s}...]} grouped by suit
    (s,h,d,c order) and rank high->low -- the same display order the desktop
    GUI uses for the N/S hands."""
    by_suit = {s: [] for s in range(4)}
    for c in hand:
        by_suit[c.suit].append(c.rank)
    out = []
    # display order: spades, hearts, diamonds, clubs
    for s in (3, 2, 1, 0):
        for r in sorted(by_suit[s], reverse=True):
            out.append({"r": r, "s": s})
    return out


def bid_display(b) -> str:
    return "Pass" if b is None else b.display


def build() -> dict:
    winexe = ROOT / "winexe"
    levels = load_all_levels(winexe)
    payload = {"levels": []}
    for lv in levels:
        deals = []
        for i, rec in enumerate(lv.records):
            sol = rec.solution
            if sol is None or sol.deal is None:
                continue
            # skip records whose md value is corrupt in the original data
            # (the parser leaves a seat under-/over-filled); they can't be
            # played and would render a broken board.
            if not validate_deal(sol.deal):
                continue
            contract = None
            if sol.contract is not None:
                decl, level, suit = sol.contract
                contract = {"seat": decl, "level": level, "suit": suit,
                            "text": "%d%s" % (level, "NT" if suit == "n" else suit.upper())}
            deals.append({
                "name": rec.name,
                "idx": i,
                "vuln": sol.vuln or "",
                "contract": contract,
                "hcp": [sol.deal.hcp(s) for s in range(4)],
                "hands": [hand_to_cards(sol.deal.hands[s]) for s in range(4)],
                "auction": [
                    {"seat": s, "bid": bid_display(b)}
                    for s, b in sol.auction
                ],
                "captions": [str(p) for p in sol.captions],
            })
        payload["levels"].append({
            "level": lv.number,
            "series": lv.series_letter,
            "deals": deals,
        })
    return payload


def main() -> int:
    data = build()
    out = Path(__file__).resolve().parent / "deals.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    total = sum(len(l["deals"]) for l in data["levels"])
    print("wrote %s  (%d deals across %d levels, %d bytes)"
          % (out.name, total, len(data["levels"]), out.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
