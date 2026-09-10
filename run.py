"""Entry point for the Bridge Master 2000 Python reimplementation.

Usage:
    python run.py            # launch the Tkinter GUI
    python run.py --demo     # run a short headless play-through
    python run.py list       # list levels and deals
    python run.py <level> <deal>   # load a specific deal in the GUI

Example:
    python run.py 1 A1
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
WINEXE = ROOT / "winexe"


def _list() -> None:
    from bm2000 import levels

    ls = levels.load_all_levels(WINEXE)
    for l in ls:
        print("Level %d  series=%s  records=%d  deals=%d" % (
            l.number, l.series_letter, l.deal_count(), l.valid_deal_count()
        ))
        for r in l.records:
            if r.has_deal:
                print("    %s   vuln=%s" % (r.name, r.vuln or "?"))


def _demo() -> None:
    from bm2000 import levels
    from bm2000.replay import play_deal

    ls = levels.load_all_levels(WINEXE)
    if not ls:
        print("no levels found")
        return
    lv = ls[0]
    rec = next(r for r in lv.records if r.has_deal)
    print("Playing deal %s (level %d)" % (rec.name, lv.number))
    rep = play_deal(rec.solution.deal, rec.solution.contract, rec.solution)
    print("  South: %s" % rec.deal.hand_str(0))
    print("  North: %s" % rec.deal.hand_str(2))
    print("  Contract: %s  (auction: %s)" % (
        rec.solution.contract,
        " ".join((b.display if b else "p") for _s, b in rec.solution.auction)))
    won = sum(1 for t in rep.tricks if t.cards[0][0] in (0, 2))
    print("  Tricks: NS %d  EW %d" % (won, 13 - won))
    print("Deal over after %d tricks (%d cards)." % (len(rep.tricks), len(rep.flat)))


def _gui(level: str = "", deal: str = "", splash: bool = True) -> None:
    import tkinter as tk
    from bm2000.gui import App, AboutDialog

    root = tk.Tk()
    root.withdraw()
    if splash:
        AboutDialog(WINEXE).wait_window()
        root.deiconify()
    app = App(root, WINEXE)
    if level and deal:
        root.update()
        app._lazy_load()
        root.update()
        app.level_combo.current(int(level) - 1)
        app._on_level()
        names = [r.name for r in app.deck]
        app.deal_combo.current(names.index(deal) if deal in names else 0)
        app._on_deal()
        app._start()
    elif level:
        root.update()
        app._lazy_load()
        root.update()
        app.level_combo.current(int(level) - 1)
        app._on_level()
    root.mainloop()


def _play(level: str = "", deal: str = "") -> None:
    """Play a deal headless with the simple AI; print the result."""
    from bm2000 import levels
    from bm2000.replay import play_deal

    ls = levels.load_all_levels(WINEXE)
    lv = ls[int(level) - 1]
    recs = [r for r in lv.records if r.has_deal]
    rec = next((r for r in recs if r.name.lower().replace(".lin", "") == deal.lower()),
               recs[0])
    rep = play_deal(rec.solution.deal, rec.solution.contract, rec.solution)
    decl, level, suit = rec.solution.contract
    # the declarer side is declarer + dummy (partner); they must take
    # level + 6 tricks (a 1-level contract needs 7, a 4-level major 10, ...)
    won = sum(1 for t in rep.tricks if t.cards[0][0] in (decl, (decl + 2) % 4))
    res = won - (level + 6)
    print("Deal %s  contract %s  declarer tricks %d (needs %d)  -> %s" % (
        rec.name, "%s%s" % (level, suit.upper() if suit != "n" else "NT"),
        won, level + 6, "MADE" if res >= 0 else "%d down" % abs(res)))


def main(argv) -> None:
    args = argv[1:]
    if not args or args[0] == "gui":
        arg1 = argv[2] if len(argv) > 2 else ""
        arg2 = argv[3] if len(argv) > 3 else ""
        _gui(arg1, arg2, splash=(len(argv) <= 1))
    elif args[0] == "--demo":
        _demo()
    elif args[0] == "list":
        _list()
    elif args[0] == "play":
        _play(args[1] if len(args) > 1 else "1",
              args[2] if len(args) > 2 else "")
    elif args[0].isdigit():
        _gui(args[0], args[1] if len(args) > 1 else "", splash=False)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
