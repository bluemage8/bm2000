"""Tkinter GUI for the Bridge Master 2000 re-implementation.

Matches the original program's UI and game logic (see analysis/SPEC_orig.md
and analysis/GAPS.md).

Layout (original window is 800x576, client 794x547):
  * TOC: product illustration on the left with the 5 skill-level buttons,
    a color-coded deal list on the right (result marks: check / X / ?),
    a User ID edit at the bottom-left, and a Win95 toolbar along the bottom.
  * Play view: a green table.  North (dummy) is on top, South (declarer) at
    the bottom, both face-up (they are the two hands *you* play).  West and
    East are on the sides, face-down (the computer's defense).  The bidding
    and contract are shown at the top, the current trick in the middle, and a
    "confirm end of trick" narration box appears after each trick.

Gameplay (faithful to the original's "About Bridge Master's play"):
  * You play BOTH South (declarer) and North (dummy).
  * The computer plays East and West and is programmed to try to defeat the
    contract; the defense's cards are played automatically.
  * Opening lead / follow-suit / trump rules are enforced.
  * Take back last play; Claim the contract only after 5 tricks; then the
    end-of-deal dialog offers Restart / Show answer (bridge movie) / Next deal,
    plus an expert rating.
"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter
from typing import Dict, List, Optional, Tuple

from . import cards
from .cards import (
    EAST, NORTH, SEAT_NAMES, SEAT_LETTERS, SOUTH, WEST,
    RANK_CHARS, SUIT_SYMBOL, Card, Deal,
)
from .levels import Level, load_all_levels
from .replay import _trump, play_deal
from .script import Solution
from .sound import Sound

# Windows 95 palette -----------------------------------------------------------
WIN_BG = "#f0f0f0"
WIN_3D_DK = "#808080"
WIN_3D_LT = "#ffffff"
# The five level-button / deal-list accent colors (to match the original's
# color-coded deals).  Order 1..5.
LEVEL_COLORS = ["#cc2222", "#22aa22", "#2244cc", "#ccaa00", "#aa22aa"]
LEVEL_PASTELS = ["#ffd7d7", "#d7ffd7", "#d7d7ff", "#ffffd7", "#ffd7ff"]
# felt / table
FELT = "#0b5d2e"
FELT_EDGE = "#063d1e"
# deal background (non-dummy) vs dummy color vs current-trick color (from HLP)
DEAL_BG = "#eef0e8"
DUMMY_BG = "#fff3c4"
TRICK_BG = "#fffbe0"
PLAYED_DIM = "#b9b9b9"

# exact UI strings lifted from the original's resources / help file ------------
TITLES = {
    "toc": "Bridge Master 2000 - Table of Contents",
    "play": "Bridge Master 2000 - Skill Level %d - Series %s - Deal %d",
}


def _vuln_text(code: str) -> str:
    c = (code or "").strip()
    table = {
        "": "?", "0": "None", "1": "NS", "2": "EW", "3": "Both",
        "00": "None", "01": "NS", "10": "EW", "11": "Both",
        "010": "NS", "100": "EW", "110": "Both", "0000": "None",
        "0200": "None",
    }
    v = table.get(c)
    return v if v else (c or "?")


def _contract_text(contract) -> str:
    if not contract:
        return "Pass out"
    _decl, lvl, suit = contract
    if suit == "n":
        return "%dNT" % lvl
    return "%d%s" % (lvl, suit.upper())


def _suit_symbol(suit: int) -> str:
    return SUIT_SYMBOL[suit]


# Bridge-master "experts" used for the end-of-deal rating (name list from the
# original's credits/resources, kept here for the rating display).
_EXPERTS = [
    "Kokish", "Zia", "Hamman", "Rosenberg", "Juster", "Lawrence",
    "Marston", "McKenzie", "Meckstroth", "Rodwell", "Auken", "Gitelman",
    "Flower", "Goren", "Blue", "Robins", "Parker", "Poliakov", "Pris",
    "Rubens", "Schwartz", "Truscott", "Woolsey", "Wheeler",
]


# ---------------------------------------------------------------------------- #
#  About splash
# ---------------------------------------------------------------------------- #
class AboutDialog(tk.Tk):
    def __init__(self, winexe) -> None:
        super().__init__()
        self.title("About Bridge Master 2000")
        self.resizable(False, False)
        self.configure(bg=WIN_BG)
        body = tk.Frame(self, bg=WIN_BG)
        body.pack(padx=28, pady=18)
        tk.Label(body, text="Bridge Master 2000", bg=WIN_BG,
                 font=("Times New Roman", 22, "bold")).pack(anchor="w")
        tk.Label(body, text="Audrey Grant's Better Bridge Edition", bg=WIN_BG,
                 font=("Times New Roman", 12, "italic")).pack(anchor="w", pady=(4, 12))
        for line in (
            "Bridge Base Inc.",
            "Copyright  1999-2001 Bridge Base Inc.",
            "(416) 322-8316",
            "",
            "A declarer-bridge teaching program:",
            "5 skill levels, ~530 deals.",
            "",
            "You are the declarer (South) and the dummy (North).",
            "The computer plays the defense (East and West).",
        ):
            tk.Label(body, text=line, bg=WIN_BG,
                     font=("MS Sans Serif", 9), anchor="w").pack(anchor="w")
        tk.Button(body, text="Ok", command=self.destroy, width=8,
                  relief="raised").pack(pady=(18, 0))
        self.protocol("WM_DELETE_WINDOW", self.destroy)


# ---------------------------------------------------------------------------- #
#  Card rendering (picture-style text cards on a canvas)
# ---------------------------------------------------------------------------- #
class CardWidget:
    """Draws a single card as a rectangle + corner index + big suit pip."""

    RED = "#c01818"
    BLACK = "#101010"

    @staticmethod
    def draw(cv: "tk.Canvas", x: int, y: int, w: int, h: int, card: Card,
             face_up: bool = True, dim: bool = False, highlight: bool = False) -> None:
        if not face_up:
            # face-down (defense) card
            cv.create_rectangle(x, y, x + w, y + h, fill="#3355aa",
                                outline="#101a40", width=1)
            cv.create_rectangle(x + 2, y + 2, x + w - 2, y + h - 2,
                                fill="none", outline="#5a79c8", width=1)
            return
        fill = "#c9c9c9" if dim else "#ffffff"
        border = "#7a7a7a" if dim else "#404040"
        if highlight:
            fill, border = "#fff3b0", "#c9a200"
        cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=border,
                            width=1)
        color = CardWidget.RED if card.suit in (1, 2) else CardWidget.BLACK
        if dim:
            color = PLAYED_DIM
        r = RANK_CHARS[card.rank]
        sym = _suit_symbol(card.suit)
        # corner-index font scales with the card box (capped so it still fits)
        fs = max(9, min(18, w // 2, h // 3))
        # top-left corner index (rank over symbol)
        cv.create_text(x + 1, y + 1, text=r, anchor="nw", fill=color,
                       font=("Consolas", fs, "bold"))
        cv.create_text(x + 1, y + 1 + fs, text=sym, anchor="nw", fill=color,
                       font=("Consolas", fs - 1))
        # bottom-right corner index (rotated look approximated by right anchor)
        cv.create_text(x + w - 1, y + h - 1, text=r, anchor="se", fill=color,
                       font=("Consolas", fs, "bold"))
        cv.create_text(x + w - 1, y + h - 1 - fs, text=sym, anchor="se",
                       fill=color, font=("Consolas", fs - 1))


# ---------------------------------------------------------------------------- #
#  Main application
# ---------------------------------------------------------------------------- #
class App:
    def __init__(self, root: tk.Tk, winexe) -> None:
        self.root = root
        self.winexe = winexe
        self.levels: List[Level] = []
        self.deck: List = []
        self.sound = Sound(winexe)
        self.cur_level = 0
        self.cur_deal_idx = 0
        self.results: Dict[Tuple[int, int], str] = {}
        self.user_id = "Ace"
        self.in_play = False
        self.play_state: Optional["_PlayState"] = None
        self.last_played: Optional[Tuple[int, int]] = None

        # Original client area is 794x547; add a little for the title bar so
        # the whole window matches the original's 800x576 footprint.
        self.root.title(TITLES["toc"])
        self.root.geometry("794x547+100+80")
        self.root.configure(bg=WIN_BG)
        self.root.minsize(760, 520)

        self._build_menu()
        self._build_toolbar()
        self._build_toc()
        root.after(120, self._lazy_load)

    # -- menu --------------------------------------------------------------- #
    def _build_menu(self):
        mb = tk.Menu(self.root)
        self.root.config(menu=mb)
        m_file = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="File", menu=m_file)
        m_file.add_command(label="New Deal", command=self._to_toc)
        m_file.add_command(label="Replay deal", command=self._replay)
        m_file.add_command(label="Replay all", command=self._replay_all)
        m_file.add_separator()
        m_file.add_command(label="Exit", command=self.root.destroy)
        m_opt = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Options", menu=m_opt)
        m_opt.add_command(label="Program Options...", command=self._options)
        m_opt.add_command(label="Restore defaults", command=self._options)
        m_help = tk.Menu(mb, tearoff=0)
        mb.add_cascade(label="Help", menu=m_help)
        m_help.add_command(label="Bridge Master 2000 Help", command=self._help)
        m_help.add_command(
            label="About Bridge Master 2000",
            command=lambda: AboutDialog(self.winexe).wait_window())
        m_help.add_command(
            label="About Bridge Base Inc.",
            command=lambda: messagebox.showinfo(
                "About Bridge Base Inc.", "Bridge Base Inc.\n(416) 322-8316\n"))

    def _help(self):
        messagebox.showinfo(
            "Bridge Master 2000 Help",
            "Select a skill level with the buttons on the left.\n\n"
            "Click a deal in the list to play it.\n\n"
            "You are the declarer (South) and the dummy (North).\n"
            "Click a card in your hand to play it.  The computer plays the\n"
            "defense (East and West) and tries to defeat your contract.\n\n"
            "Use Take back to undo a card, Claim (after 5 tricks) to stop,\n"
            "and Replay to start the deal over.\n")

    def _options(self):
        messagebox.showinfo(
            "Program Options",
            "Options: pictures vs. hand diagrams, big/small deal, hide/show\n"
            "played cards, annotate, animate, sound, confirm end of trick.\n\n"
            "(The re-implementation shows hand-diagram text cards.)")

    # -- toolbar ------------------------------------------------------------ #
    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=WIN_BG, relief="raised", bd=1, height=30)
        tb.pack(side="bottom", fill="x")
        tb.pack_propagate(False)

        def sep():
            f = tk.Frame(tb, width=2, bg=WIN_3D_DK)
            f.pack(side="left", fill="y", pady=2)

        def b(text, cmd, tip=""):
            # width auto-sizes to the (short) label; the FULL original tooltip
            # string is set on the button so hovering shows the exact original
            # wording (e.g. "Take back last play").
            # fixed narrow width (icon-like, like the original).  The full
            # original tooltip is shown on hover; the face text is a short hint
            # (it may clip for the longest labels -- the tooltip has the truth).
            btn = tk.Button(tb, text=text, relief="raised", bd=1, width=5,
                            bg=WIN_BG, command=cmd, takefocus=0,
                            font=("Segoe UI", 7), padx=1, pady=0)
            btn.pack(side="left", padx=1, pady=2)
            if tip:
                btn.bind("<Enter>", lambda e, w=btn, t=tip: self._show_tip(w, t))
                btn.bind("<Leave>", lambda e: self._hide_tip())
            return btn

        # NOTE: the button TOOLTIPS use the original bm2000.exe English resource
        # strings (verified from the binary + the HLP): "Replay deal",
        # "Take back last play", "Claim the contract", "Open bridge movie",
        # "First page of this chapter", "Big deal", "Hide played cards", etc.
        # The button face text is a short form so the whole toolbar fits the
        # 794px window (the original's toolbar buttons are icon-sized).
        g = tk.Frame(tb, bg=WIN_BG); g.pack(side="left", padx=(4, 0), fill="y")
        b("First", self._first_deal, "First board").pack(in_=g, side="left")
        b("Prev", self._prev_deal, "Previous board").pack(in_=g, side="left", padx=1)
        b("Next", self._next_deal, "Next deal").pack(in_=g, side="left", padx=1)
        b("Last", self._last_deal, "Last board").pack(in_=g, side="left", padx=1)

        sep()
        g = tk.Frame(tb, bg=WIN_BG); g.pack(side="left", fill="y")
        b("Replay", self._replay, "Replay deal").pack(in_=g, side="left")
        b("Step", self._step_forward,
          "Play the next card in the deal").pack(in_=g, side="left", padx=1)
        b("Take back", self._step_back, "Take back last play").pack(in_=g, side="left", padx=1)
        self.btn_claim = b("Claim", self._claim, "Claim the contract (after 5 tricks)")
        self.btn_claim.pack(in_=g, side="left", padx=1)

        sep()
        g = tk.Frame(tb, bg=WIN_BG); g.pack(side="left", fill="y")
        self.btn_movie = b("Movie", self._toggle_movie,
                           "Open the bridge movie")
        self.btn_movie.pack(in_=g, side="left")
        b("1st", self._movie_first, "First page of this chapter").pack(in_=g, side="left", padx=1)
        b("Prev", self._movie_prev, "Previous page").pack(in_=g, side="left", padx=1)
        b("Next", self._movie_next, "Next page").pack(in_=g, side="left", padx=1)
        b("Last", self._movie_last, "Last card in sequence").pack(in_=g, side="left", padx=1)

        sep()
        g = tk.Frame(tb, bg=WIN_BG); g.pack(side="left", fill="y")
        self.btn_size = b("Big", self._toggle_card_size, "Big deal / Small deal")
        self.btn_size.pack(in_=g, side="left")
        self.btn_hide = b("Show", self._toggle_hide, "Show / Hide played cards")
        self.btn_hide.pack(in_=g, side="left", padx=1)

        sep()
        self.btn_sound = b("Sound", self._toggle_sound, "Sound effects on / off")
        self.btn_sound.pack(side="left", padx=1)
        b("Help", self._help, "Help").pack(side="left", padx=(4, 4))

    # -- small tooltip helper (tkinter has no native tooltips) --------------- #
    def _show_tip(self, widget, text):
        tw = getattr(self, "_tipwin", None)
        if tw is not None and tw.winfo_exists():
            tw.destroy()
        tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.update_idletasks()
        x = widget.winfo_rootx() + 2
        y = widget.winfo_rooty() - 18
        tw.geometry("+%d+%d" % (x, y))
        tk.Label(tw, text=text, bg="#ffffe1", fg="black",
                 font=("MS Sans Serif", 8), bd=1, relief="solid").pack(padx=2, pady=1)
        self._tipwin = tw

    def _hide_tip(self):
        tw = getattr(self, "_tipwin", None)
        if tw is not None and tw.winfo_exists():
            tw.destroy()
        self._tipwin = None

    # -- TOC view ----------------------------------------------------------- #
    def _build_toc(self):
        self.toc = tk.Frame(self.root, bg=WIN_BG)
        self.toc.pack(side="top", fill="both", expand=True)
        self.toc.pack_forget()  # shown via _show_toc

        # status line (bottom) -- packed first so it reserves space
        self.status = tk.Label(self.toc, text="Loading deals...", bg=WIN_BG,
                               anchor="w", relief="sunken", bd=1,
                               font=("MS Sans Serif", 8))
        self.status.pack(side="bottom", fill="x")

        # ---- level buttons column (left) ---- #
        # (The original's product-box info panel is intentionally omitted per
        #  request; only the skill-level buttons and the deal list remain.)
        self.sort_mode = "name"
        lvcol = tk.Frame(self.toc, bg=WIN_BG, width=110)
        lvcol.pack(side="left", fill="y", padx=4, pady=2)
        lvcol.pack_propagate(False)
        self.level_btns: List[tk.Button] = []
        for i in range(5):
            btn = tk.Button(
                lvcol, text="Level %d" % (i + 1), width=9, height=2,
                bg=LEVEL_COLORS[i], fg="white",
                font=("Arial", 12, "bold"),
                activebackground=LEVEL_COLORS[i],
                relief="raised", bd=2,
                command=lambda n=i: self._select_level(n))
            btn.pack(padx=8, pady=6)
            self.level_btns.append(btn)

        # ---- right: the deal list (color-coded table) ---- #
        outer = tk.Frame(self.toc, bg=WIN_BG, relief="sunken", bd=2)
        outer.pack(side="left", fill="both", expand=True, padx=2, pady=2)
        self.list_canvas = tk.Canvas(outer, bg="#ffffff", highlightthickness=0)
        self.list_canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(outer, orient="vertical",
                           command=self.list_canvas.yview)
        sb.pack(side="right", fill="y")
        self.list_canvas.configure(yscrollcommand=sb.set)
        self._last_list_w = 0
        self.list_canvas.bind("<Configure>", self._on_list_configure)
        self.list_canvas.bind("<Button-1>", self._on_deal_click)
        self._deal_items: List[dict] = []
        self.toc_id = None

    def _on_list_configure(self, event):
        # Only redraw when the canvas width genuinely changes and has
        # settled (avoids the layout drifting during a resize cascade).
        w = event.width
        if w >= 60 and abs(w - self._last_list_w) > 3:
            self._last_list_w = w
            self._rebuild_deal_list()

    def _show_toc(self):
        self._clear_center()
        self.toc.pack(side="top", fill="both", expand=True)
        if self.levels and not self.deck and self.cur_level < len(self.levels):
            self._select_level(self.cur_level)

    def _clear_center(self):
        for f in (getattr(self, "toc", None), getattr(self, "play", None)):
            if f is not None and f.winfo_exists():
                f.pack_forget()

    # -- lazy load ---------------------------------------------------------- #
    def _lazy_load(self):
        self.levels = load_all_levels(self.winexe)
        if self.levels:
            self._select_level(0)
        self._show_toc()
        if self.levels:
            self.status.config(text="%d deals at level %d.  Click a deal to play."
                                % (len(self.deck), self.levels[0].number))

    def _select_level(self, n: int):
        if n < 0 or n >= len(self.levels):
            return
        self.cur_level = n
        lv = self.levels[n]
        self.deck = [r for r in lv.records if r.has_deal]
        for i, b in enumerate(self.level_btns):
            b.config(relief="sunken" if i == n else "raised")
        # color-code the list rows to the level
        self._rebuild_deal_list()
        self.status.config(text="Level %d: %d deals.  Click a deal to play."
                                % (lv.number, len(self.deck)))

    def _sort(self, mode: str):
        self.sort_mode = mode
        if mode == "result":
            def key(r, i):
                return {"made": 0, "down": 1, "aborted": 2}.get(
                    self.results.get((self.cur_level, i)), 3)
            order = sorted(range(len(self.deck)), key=lambda i: key(self.deck[i], i))
        else:
            order = list(range(len(self.deck)))
        saved = self.deck
        self.deck = [saved[i] for i in order]
        self._rebuild_deal_list()

    def _rebuild_deal_list(self):
        cv = getattr(self, "list_canvas", None)
        if cv is None or not cv.winfo_exists():
            return
        cv.delete("all")
        self._deal_items = []
        lv = self.levels[self.cur_level] if self.levels else None
        series = lv.series_letter if lv else "?"
        W = cv.winfo_width() or 640
        H = cv.winfo_height() or 520
        rowh = 22
        x0, x1 = 3, W - 3
        accent = LEVEL_COLORS[self.cur_level]
        pastel = LEVEL_PASTELS[self.cur_level]
        for i, rec in enumerate(self.deck):
            code = "%s-%d" % (series, i + 1)
            y = 3 + i * rowh
            if i % 2 == 1:
                cv.create_rectangle(x0, y, x1, y + rowh, fill="#eceade", outline="")
            # full-width color-coded row stripe (matches the original's
            # color-coded deal list)
            cv.create_rectangle(x0, y, x0 + 6, y + rowh, fill=accent, outline="")
            # deal code
            fb = rec.solution.contract if rec.solution else None
            cbtxt = _contract_text(fb) if fb else "-"
            res = self.results.get((self.cur_level, i))
            mark, mcol = "", "black"
            if res == "made":
                mark, mcol = "\u2713", "#0a7a0a"   # check = contract made
            elif res == "down":
                mark, mcol = "\u2718", "#b00000"    # X   = defeated
            elif res == "aborted":
                mark, mcol = "?", "#666666"
            was_last = self.last_played == (self.cur_level, i)
            fg = "#9a9a9a" if was_last else "black"
            cv.create_text(x0 + 12, y + rowh // 2, text=code, anchor="w",
                           fill=fg, font=("Consolas", 10, "bold"))
            # contract in the middle
            cv.create_text(W // 2, y + rowh // 2, text=cbtxt, anchor="center",
                           fill="#222", font=("MS Sans Serif", 9))
            # result mark at the right (HLP: mark appears at the right side)
            cv.create_text(x1 - 8, y + rowh // 2, text=mark, anchor="e",
                           fill=mcol, font=("Segoe UI", 10, "bold"))
            self._deal_items.append({"x": x0, "y": y, "x2": x1, "y2": y + rowh,
                                     "idx": i, "code": code})
        total = max(H, 3 + len(self.deck) * rowh + 4)
        cv.config(scrollregion=(0, 0, W, total))

    def _on_deal_click(self, event):
        for it in self._deal_items:
            if it["x"] <= event.x <= it["x2"] and it["y"] <= event.y <= it["y2"]:
                self.last_played = (self.cur_level, it["idx"])
                self._play_deal(it["idx"])
                return

    # -- navigation --------------------------------------------------------- #
    def _to_toc(self):
        self.in_play = False
        self.play_state = None
        self.root.title(TITLES["toc"])
        self._show_toc()
        self._rebuild_deal_list()

    def _first_deal(self):
        if self.deck:
            self.play_deal_idx_to(0)

    def _prev_deal(self):
        if self.deck:
            self.play_deal_idx_to((self.cur_deal_idx - 1) % len(self.deck))

    def _next_deal(self):
        if self.deck:
            self.play_deal_idx_to((self.cur_deal_idx + 1) % len(self.deck))

    def _last_deal(self):
        if self.deck:
            self.play_deal_idx_to(len(self.deck) - 1)

    def play_deal_idx_to(self, i: int):
        if 0 <= i < len(self.deck):
            self.cur_deal_idx = i
            self._play_deal(i)

    # -- play --------------------------------------------------------------- #
    def _play_deal(self, idx: int):
        if idx < 0 or idx >= len(self.deck):
            return
        rec = self.deck[idx]
        sol = rec.solution
        rep = play_deal(sol.deal, sol.contract, sol)
        self.play_state = _PlayState(self, rec, sol, rep)
        self.in_play = True
        series = self.levels[self.cur_level].series_letter
        self.cur_deal_idx = idx
        self.root.title(TITLES["play"] % (self.cur_level + 1, series, idx + 1))
        self._clear_center()
        self._build_play_view()
        self.play_state._render()
        # In our model the defense (West) opens, so kick it off.
        self.play_state._kicked_off()

    def _build_play_view(self):
        pv = tk.Frame(self.root, bg=WIN_BG)
        pv.pack(side="top", fill="both", expand=True)
        self.play = pv

        # top strip: bidding + contract + vuln + deal id
        self.top = tk.Frame(pv, bg="white")
        self.top.pack(side="top", fill="x", pady=(0, 1))
        self.auction_var = tk.StringVar()
        tk.Label(self.top, textvariable=self.auction_var, bg="white",
                 font=("Consolas", 10), anchor="w").pack(side="left", padx=6, pady=(2, 0))
        sol = self.play_state.sol
        parts = ["%s %s" % (SEAT_LETTERS[s], (bb.display if bb else "Pass"))
                 for s, bb in sol.auction]
        self.auction_var.set("  ".join(parts))
        info = tk.Frame(self.top, bg="white"); info.pack(side="left", padx=10, pady=2)
        tk.Label(info, text="Contract: %s   Vuln: %s   HCP S:%d N:%d" % (
            _contract_text(sol.contract), _vuln_text(sol.vuln),
            sol.deal.hcp(SOUTH), sol.deal.hcp(NORTH)),
            bg="white", font=("MS Sans Serif", 9, "bold")).pack()

        # the table canvas
        self.board = tk.Canvas(pv, bg=FELT, highlightthickness=0)
        self.board.pack(side="top", fill="both", expand=True, padx=2, pady=1)
        self.board.bind("<Button-1>", self._on_board_click)
        self.board.bind("<Configure>", lambda e: self.play_state and self.play_state._render())

        # NS / EW trick strip
        self.strip = tk.Label(pv, bg="#fff3c4", relief="sunken", bd=1,
                              font=("Consolas", 11, "bold"),
                              text="NS  0      EW  0")
        self.strip.pack(side="top", fill="x", pady=(0, 1))

        # narration / confirm box
        self.narr = tk.Text(pv, height=4, wrap="word", bg="white",
                            relief="sunken", bd=1, font=("MS Sans Serif", 9),
                            state="disabled")
        self.narr.pack(side="top", fill="x", padx=2, pady=(1, 2))

    def _set_narr(self, text: str):
        self.narr.configure(state="normal")
        self.narr.delete("1.0", "end")
        self.narr.insert("1.0", text or " ")
        self.narr.configure(state="disabled")

    def _on_board_click(self, event):
        if self.play_state:
            self.play_state._on_click(event)

    # -- toolbar actions ---------------------------------------------------- #
    def _step_forward(self):
        if self.play_state and not self.play_state.movie_mode:
            self.play_state._advance()

    def _step_back(self):
        if self.play_state:
            self.play_state._undo()

    def _replay(self):
        if self.play_state:
            self.play_state._reset()

    def _replay_all(self):
        if self.play_state:
            self.play_state._reset()
            self.play_state._auto_complete()

    def _claim(self):
        ps = self.play_state
        if not ps:
            return
        if ps.tricks_played >= 5:
            ps._finish()
            self._show_end_dialog()
        else:
            messagebox.showinfo(
                "Claim",
                "You may claim the contract only after five tricks have been played.\n"
                "(You are at trick %d.)" % (ps.tricks_played))

    def _toggle_movie(self):
        if self.play_state:
            self.play_state.movie_mode = not self.play_state.movie_mode
            if self.play_state.movie_mode:
                self.play_state.movie_page = 0
            self.play_state._render()
            self.btn_movie.config(relief="sunken" if self.play_state.movie_mode else "raised")

    def _movie_n_pages(self) -> int:
        return len(self.play_state.narr_pages) if self.play_state else 0

    def _movie_first(self):
        """'First page of this chapter' -- go to the start of the movie."""
        if self.play_state:
            self.play_state.movie_mode = True
            self.play_state.movie_page = 0
            self.play_state._render()
            self.btn_movie.config(relief="sunken")

    def _movie_prev(self):
        """'Previous page'."""
        if self.play_state:
            self.play_state.movie_mode = True
            self.play_state.movie_page = max(0, self.play_state.movie_page - 1)
            self.play_state._render()

    def _movie_next(self):
        """'Next card in sequence' / next page."""
        if self.play_state:
            self.play_state.movie_mode = True
            self.play_state.movie_page = min(
                self._movie_n_pages() - 1, self.play_state.movie_page + 1)
            self.play_state._render()

    def _movie_last(self):
        """'Last card in sequence' -- jump to the last narration page."""
        if self.play_state:
            self.play_state.movie_mode = True
            n = self._movie_n_pages()
            self.play_state.movie_page = n - 1 if n else 0
            self.play_state._render()

    def _toggle_card_size(self):
        """'Big deal' / 'Small deal' modes."""
        if self.play_state:
            self.play_state.big = not self.play_state.big
            self.btn_size.config(text="Small" if self.play_state.big else "Big")
            self.play_state._render()

    def _toggle_hide(self):
        """'Show played cards' / 'Hide played cards'."""
        if self.play_state:
            self.play_state.hide_played = not self.play_state.hide_played
            self.btn_hide.config(text="Hide" if self.play_state.hide_played else "Show")
            self.play_state._render()

    def _toggle_sound(self):
        """'Sound effects on / off'."""
        self.sound.enabled = not self.sound.enabled
        self.btn_sound.config(text="Sound: On" if self.sound.enabled else "Sound: Off")

    # -- end of deal -------------------------------------------------------- #
    def _show_end_dialog(self):
        ps = self.play_state
        won, level = ps._score()
        made = won >= level
        expert = _EXPERTS[ps._expert_idx] if made else None
        key = (self.cur_level, self.cur_deal_idx)
        self.results[key] = "made" if made else "down"
        self.last_played = key
        contract = _contract_text(ps.sol.contract)
        if ps.sol.contract is None:
            sub = "Pass out -- no contract reached."
            big = "PASS"
        else:
            big = "DEAL" if made else "FAILED"
            if made:
                sub = "%s  made by %d.   Expert rating: %s" % (
                    contract, won - level, expert or "")
            else:
                sub = "%s  down by %d." % (contract, level - won)
        self._flash_end_dialog(big, sub, won, level, made)

    def _flash_end_dialog(self, big: str, sub: str, won: int, level: int,
                          made: bool):
        """A flashy, animated end-of-deal dialog.

        Big word ("DEAL" / "FAILED") in gold (made) or red (down) that pulses,
        a trick-counter line, and three actions: Restart / Show answer / Next.
        """
        dlg = tk.Toplevel(self.root)
        dlg.title("End of deal")
        dlg.configure(bg="#0e1430")
        dlg.resizable(False, False)
        # center over the main window
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 460) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 260) // 2
        dlg.geometry("460x260+%d+%d" % (x, y))
        dlg.transient(self.root)
        dlg.grab_set()
        # focus + modal behaviour via return/cancel
        dlg.protocol("WM_DELETE_WINDOW", lambda: dlg.cancel())
        # -- the flashy headline (animated) -- #
        headline = tk.Label(dlg, text="DEAL" if made else "FAILED",
                            font=("Arial", 52, "bold"),
                            bg="#0e1430",
                            fg="#ffd24a" if made else "#ff5a4a")
        headline.pack(pady=(18, 0))
        # -- score line -- #
        score = tk.Label(dlg, text="NS  %d      EW  %d      (contract needs %d)"
                         % (won, 13 - won, level),
                         font=("Consolas", 13, "bold"),
                         bg="#0e1430", fg="#cfe8cf")
        score.pack(pady=(6, 0))
        # -- the explanatory sub line -- #
        sub_lbl = tk.Label(dlg, text=sub, font=("Segoe UI", 11),
                           bg="#0e1430", fg="#ffffff", wraplength=400,
                           justify="center")
        sub_lbl.pack(pady=(8, 4))
        # -- buttons -- #
        btns = tk.Frame(dlg, bg="#0e1430")
        btns.pack(pady=(14, 14))
        b_restart = tk.Button(btns, text="Restart deal", width=14, height=1,
                              relief="raised", bd=2, bg="#1f6feb", fg="white",
                              activebackground="#1f6feb",
                              activeforeground="white",
                              font=("Segoe UI", 10, "bold"),
                              command=lambda: (dlg.destroy(), self._replay()))
        b_answer = tk.Button(btns, text="Show answer", width=14, height=1,
                             relief="raised", bd=2, bg="#8a5a2a", fg="white",
                             activebackground="#8a5a2a",
                             activeforeground="white",
                             font=("Segoe UI", 10, "bold"),
                              command=lambda: (
                                  dlg.destroy(), self._start_answer_movie(),
                                  self.movie_auto_next()))
        b_next = tk.Button(btns, text="Next deal", width=14, height=1,
                           relief="raised", bd=2, bg="#2ea44f", fg="white",
                           activebackground="#2ea44f", activeforeground="white",
                           font=("Segoe UI", 10, "bold"),
                           command=lambda: (dlg.destroy(), self._to_toc()))
        b_restart.grid(row=0, column=0, padx=8)
        b_answer.grid(row=0, column=1, padx=8)
        b_next.grid(row=0, column=2, padx=8)
        # keyboard shortcuts
        dlg.bind("<Return>", lambda e: b_next.invoke())
        dlg.bind("<Escape>", lambda e: b_restart.invoke())
        dlg.focus_set()
        # -- pulse animation on the headline + a glow sweep -- #
        def cancel():
            dlg.grab_release()
            dlg.destroy()
        dlg.cancel = cancel
        phase = 0
        base_size = 52
        glow = "#0e1430"

        def pulse():
            nonlocal phase
            if not dlg.winfo_exists():
                return
            phase += 1
            t = (phase % 24) / 24.0
            size = base_size + int(6 * (abs(2 * t - 1) ** 1.5))
            dim = 0.45 + 0.55 * (abs(2 * t - 1) ** 1.5)
            base = (255, 210, 74) if made else (255, 90, 74)
            col = "#%02x%02x%02x" % tuple(int(c * dim) for c in base)
            headline.config(font=("Arial", size, "bold"), fg=col)
            dlg.after(45, pulse)

        pulse()

    def movie_auto_next(self):
        # advance through the movie narration automatically
        if self.play_state and self.play_state.movie_mode:
            self.root.after(2500, lambda: (self._movie_next(), self.movie_auto_next()))

    def _start_answer_movie(self):
        """'Show answer': enter the bridge-movie narration mode for the deal that
        was just played, so the expert's play-by-play captions roll page by page
        (auto-advancing via movie_auto_next).  The board keeps the final trick
        (the collected hand) so the learner can see where the deal ended."""
        ps = self.play_state
        if not ps:
            return
        ps.movie_mode = True
        ps.movie_page = 0
        ps.collecting_winner = None
        ps._render()
        if getattr(self, "btn_movie", None) is not None:
            self.btn_movie.config(relief="sunken")


# ---------------------------------------------------------------------------- #
#  Play state / board drawing
#  The actual game is an interactive playgame.PlayState (see playgame.py).
#  This wrapper renders it on the canvas and drives the GUI.
# ---------------------------------------------------------------------------- #
import bm2000.playgame as _pg

class _PlayState:
    def __init__(self, app: App, rec, sol: Solution, rep) -> None:
        self.app = app
        self.rec = rec
        self.sol = sol
        self.game = _pg.start(sol.deal, sol.contract)
        # keep the deterministic replay for the "Show answer" movie
        self.rep = rep
        self.movie_mode = False
        self.movie_page = 0
        self.big = True
        self.hide_played = False
        self.narr_pages = self._build_narration_pages()
        self._undo_stack: List = []
        # collection phase: after the 4th card is played the winning card is
        # highlighted and held for a moment before the trick is swept away.
        self.collecting_winner: Optional[int] = None
        # how long the collection hold lasts (ms) -- the "sweep" of a trick
        self.collect_ms = 1100

    # -- geometry helpers --------------------------------------------------- #
    @property
    def tricks_played(self) -> int:
        return self.game.tricks_played

    def _score(self):
        return self.game.score()

    @property
    def _expert_idx(self) -> int:
        return self.rec.start % len(_EXPERTS)

    def _build_narration_pages(self) -> List[str]:
        pages: List[str] = []
        buf: List[str] = []
        for st in self.sol.steps:
            if st.kind == "group":
                if buf:
                    pages.append(" ".join(buf)); buf = []
            elif st.kind == "caption":
                buf.append(str(st.payload))
        if buf:
            pages.append(" ".join(buf))
        return [p for p in pages if p.strip()]

    # -- hands / trick state (delegated to the interactive game) ------------ #
    def _hands_left(self) -> List[List[Card]]:
        # Display order matches the original's hand diagram: suits in the
        # order spades, hearts, diamonds, clubs, and within each suit the
        # ranks high -> low (A K Q J T 9 ... 2).
        suit_order = {3: 0, 2: 1, 1: 2, 0: 3}  # s, h, d, c
        return [sorted(h, key=lambda c: (suit_order[c.suit], -c.rank))
                for h in self.game.hands]

    def _current_trick(self) -> List[Tuple[int, Card]]:
        return self.game.trick

    def _trick_winner(self) -> Optional[int]:
        if not self.game.tricks:
            return None
        t = self.game.tricks[-1]
        return _pg.trick_winner(t, self.game.trump)

    def _to_play(self) -> Optional[int]:
        return self.game.to_play

    def _valid_cards(self) -> List[Card]:
        """The cards the user may click.

        You are the declarer and may play any *legal* card (follow suit, or
        ruff / discard when void).  All legal cards are highlighted; the rest
        are dimmed.  The defense (E/W) plays automatically.
        """
        seat = self._to_play()
        if seat not in (SOUTH, NORTH):
            return []
        return self.game.legal()

    # -- progression -------------------------------------------------------- #
    def _advance(self):
        """Auto-play defense cards one by one (with a short pause) until it is
        the human's turn or the deal ends."""
        if self.collecting_winner is not None or self.game.done:
            return
        seat = self.game.to_play
        if seat is None:
            return
        if seat in (EAST, WEST):
            self._push_undo()
            self.game.auto_defense_step()
            self._after_play()

    def _after_play(self):
        """Common follow-up after any card (human or defense) is played.

        If the 4th card of the trick was just played, hold the trick on the
        table with the winning card lit up for ``collect_ms`` -- the visible
        "collection" of the trick -- before sweeping it into the results and
        moving on to the next lead.
        """
        self._render()
        if self.game.done:
            self.app._show_end_dialog()
            return
        # a trick just closed (the trick list is now empty, a new trick pending)
        just_closed = (not self.game.trick) and bool(self.game.tricks)
        if just_closed:
            self.collecting_winner = self._trick_winner()
            self.app._set_narr(self._collected_line())
            self._render()
            self.app.root.after(self.collect_ms, self._finish_collect)
            return
        nxt = self.game.to_play
        if nxt in (EAST, WEST):
            self.app.root.after(420, self._advance)

    def _collected_line(self) -> str:
        w = self._trick_winner()
        if w is None:
            return ""
        seat = SEAT_NAMES[w]
        side = "your side" if w in (SOUTH, NORTH) else "the defense"
        return "%s takes the trick (%s) -- collecting..." % (seat, side)

    def _finish_collect(self):
        """End the collection hold and continue play."""
        self.collecting_winner = None
        if self.game.done:
            return
        # after the sweep, if the defense leads the next trick let it roll
        if self.game.to_play in (EAST, WEST):
            self.app.root.after(240, self._advance)

    def _push_undo(self):
        self._undo_stack.append((
            [list(h) for h in self.game.hands],
            self.game.leader,
            list(self.game.trick),
            self.game.won_ns,
            self.game.done))

    def _play_card(self, index_in_hand: int, seat: int):
        """Play the card the user clicked (must be a legal card for `seat`)."""
        if self.collecting_winner is not None or self.game.done:
            return
        if seat not in (SOUTH, NORTH):
            return
        hand = self._hands_left()[seat]
        if index_in_hand < 0 or index_in_hand >= len(hand):
            return
        target = hand[index_in_hand]
        if not self.game.done and seat == self.game.to_play and target in self.game.legal():
            self._push_undo()
            self.game.play(target)
            self._after_play()

    def _undo(self):
        if not self._undo_stack:
            return
        hands, leader, trick, won, done = self._undo_stack.pop()
        self.game.hands = hands
        self.game.leader = leader
        self.game.trick = trick
        self.game.won_ns = won
        self.game.done = done
        self.collecting_winner = None
        self._render()

    def _reset(self):
        self.game = _pg.start(self.sol.deal, self.sol.contract)
        self._undo_stack = []
        self.movie_mode = False
        self.movie_page = 0
        self.collecting_winner = None
        self._render()
        self._kicked_off()

    def _kicked_off(self):
        self.collecting_winner = None
        # if the very first play is the defense's, let it open
        if not self.movie_mode and self.game.to_play in (EAST, WEST):
            self.app.root.after(420, self._advance)

    def _finish(self):
        self.app._set_narr("You claim the contract.")

    def _auto_complete(self):
        """Play out the rest (declarer + defense) -- used for bridge movie."""
        guard = 0
        while not self.game.done and guard < 80:
            seat = self.game.to_play
            if seat is None:
                break
            if seat in (EAST, WEST):
                self.game.auto_defense_step()
            else:
                self.game.play(min(self.game.legal(),
                                   key=lambda c: (c.suit, c.rank)))
            self._render()
            guard += 1

    # -- click handling ----------------------------------------------------- #
    def _on_click(self, event):
        if self.movie_mode:
            return
        seat = self._to_play()
        if seat not in (SOUTH, NORTH):
            return
        b = self.app.board
        w = b.winfo_width() or 790
        h = b.winfo_height() or 420
        hand = self._hands_left()[seat]
        valid = self._valid_cards()
        dims = self._play_dims()  # N/S hands are drawn big -- hit-test matches
        cw, ch, gap = dims
        y = self._hand_y(seat, h, dims=dims)
        for i, card in enumerate(hand):
            x = self._hand_x(seat, i, len(hand), w, dims=dims)
            if x - 2 <= event.x <= x + cw + 2 and y - 2 <= event.y <= y + ch + 2:
                if card in valid:
                    self._play_card(i, seat)
                self.app._set_narr(self._hint_after(card))
                return

    def _hint_after(self, card: Card) -> str:
        return "You played the %s %s.  The defense is playing..." % (
            RANK_CHARS[card.rank], SUIT_ABBR_LOCAL[card.suit])

    # -- geometry for drawing ---------------------------------------------- #
    def _dims(self):
        # card size.  The "big" (default) mode is used for the N/S hands and the
        # played/collected trick; "small" is the compact toggle.  Big is sized
        # up so the ranks/pips are easy to read at a glance.
        big = self.big
        cw = 34 if big else 24
        ch = 46 if big else 34
        gap = 3 if big else 2
        return cw, ch, gap

    def _play_dims(self):
        """Larger size for the N/S hands and the played/collected center trick,
        so the cards you actually read and play are the big on-screen ones.  The
        face-down defense fans keep the (smaller) base _dims() size."""
        big = self.big
        cw = 40 if big else 28
        ch = 56 if big else 40
        gap = 4 if big else 2
        return cw, ch, gap

    def _hand_x(self, seat: int, i: int, n: int, w: int, dims=None) -> int:
        cw, ch, gap = dims if dims else self._dims()
        total = n * cw + (n - 1) * gap
        x0 = (w - total) // 2
        return x0 + i * (cw + gap)

    def _hand_y(self, seat: int, h: int, dims=None) -> int:
        cw, ch, gap = dims if dims else self._dims()
        if seat == SOUTH:
            return h - ch - 8
        if seat == NORTH:
            return 24
        return h // 2 - ch // 2

    def _render(self):
        app = self.app
        b = app.board
        if not b or not b.winfo_exists():
            return
        b.delete("all")
        w = b.winfo_width()
        h = b.winfo_height()
        if not w or not h or w < 100 or h < 100:
            return
        cw, ch, gap = self._dims()          # base size (defense fans)
        pd_cw, pd_ch, pd_gap = self._play_dims()  # larger: N/S hands + trick
        hands = self._hands_left()
        trick = self._current_trick()
        winner = self._trick_winner()
        valid = self._valid_cards()
        to_play = self._to_play()

        # felt with a darker border ring for a "table" look
        b.create_rectangle(0, 0, w, h, fill=FELT, outline=FELT_EDGE, width=4)

        # seat name labels (original colors the four player names)
        names = {NORTH: "NORTH  (dummy, you)", SOUTH: "SOUTH  (declarer, you)",
                 WEST: "WEST  (defense)", EAST: "EAST  (defense)"}
        labelpos = {NORTH: (w // 2, 5), SOUTH: (w // 2, h - 5),
                    WEST: (6, h // 2), EAST: (w - 6, h // 2)}
        anchors = {NORTH: "center", SOUTH: "center", WEST: "w", EAST: "e"}
        for seat in (NORTH, SOUTH, WEST, EAST):
            col = "#fff2a6" if seat in (SOUTH, NORTH) else "#dfe8df"
            b.create_text(labelpos[seat], text=names[seat], fill=col,
                          font=("Segoe UI", 9, "bold"), anchor=anchors[seat])

        pdims = (pd_cw, pd_ch, pd_gap)
        # the two hands *you* play are drawn big (N/S)
        for seat in (NORTH, SOUTH):
            hand = hands[seat]
            y = self._hand_y(seat, h, dims=pdims)
            for i, card in enumerate(hand):
                x = self._hand_x(seat, i, len(hand), w, dims=pdims)
                hl = card in valid
                CardWidget.draw(b, x, y, pd_cw, pd_ch, card, face_up=True,
                                highlight=hl)
        # the face-down defense fans stay at the base size
        for seat in (WEST, EAST):
            hand = hands[seat]
            y = self._hand_y(seat, h)
            if seat == WEST:
                x = 40
            else:
                x = w - 40 - cw
            # stack vertically, but only show count of cards as a compact fan
            for i in range(len(hand)):
                yy = y - (len(hand) - 1) * (ch * 0.5) // 2 + i * (ch * 0.5)
                self._draw_cardback(b, x, yy, cw, ch, seat)

        # current trick in the center -- while a trick is being "collected"
        # (the 4 cards are held before being swept) we keep drawing it and
        # light up the winning card in gold.  Played cards use the big size too.
        show_trick = list(trick)
        show_winner = winner
        if self.collecting_winner is not None and self.game.tricks:
            show_trick = list(self.game.tricks[-1])
            show_winner = self.collecting_winner
        if show_trick:
            cx, cy = w // 2, h // 2
            collecting = self.collecting_winner is not None
            for idx, (seat, card) in enumerate(show_trick):
                tx, ty = self._trick_pos(seat, idx, len(show_trick), cx, cy,
                                         pd_cw, pd_ch)
                is_win = (show_winner is not None and seat == show_winner)
                if is_win:
                    CardWidget.draw(b, tx - 3, ty - 3, pd_cw + 6, pd_ch + 6, card,
                                    face_up=True, dim=True, highlight=False)
                CardWidget.draw(b, tx, ty, pd_cw, pd_ch, card, face_up=True,
                                dim=False, highlight=is_win)
                if collecting:
                    b.create_text(tx + pd_cw // 2, ty - 6,
                                  text="WIN" if is_win else "",
                                  fill="#ffd24a" if is_win else "#cfe8cf",
                                  font=("Arial", 9, "bold"), anchor="s")

        # NS / EW strip
        decl = self.sol.contract[0] if self.sol.contract else None
        won = sum(1 for t in self.rep.tricks if len(t.cards) == 4
                  and (decl is None or t.cards[0][0] in (decl, (decl + 2) % 4)))
        ew = sum(1 for t in self.rep.tricks if len(t.cards) == 4) - won
        app.strip.config(text="   NS  %d        EW  %d        Trick %d/13"
                         % (won, ew, len(self.game.tricks) + (1 if self.game.trick else 0)))

        self._render_narration()

    def _draw_cardback(self, b: "tk.Canvas", x, y, cw, ch, seat):
        b.create_rectangle(x, y, x + cw, y + ch, fill="#2f4f9e", outline="#101a40")
        b.create_oval(x + cw // 2 - 3, y + ch // 2 - 3, x + cw // 2 + 3,
                      y + ch // 2 + 3, outline="#8fa8e0", fill="#2f4f9e")

    def _trick_pos(self, seat, idx, n, cx, cy, cw, ch):
        # Top-left corner of a seat's card in the current trick.  The position is
        # pinned to a FIXED cardinal anchor around the table center (cx, cy) that
        # depends ONLY on the seat -- never on idx or n.  Each seat plays at most
        # one card per trick, so as the trick fills (1..4 cards) every card lands
        # in the same spot it already occupies: the 4 cards form a stable cross
        # (NORTH top, SOUTH bottom, WEST left, EAST right) and do NOT slide when
        # a new card is added.  Placing from the card center (subtract cw/ch//2)
        # also means growing the card box (_play_dims) doesn't shift the cluster.
        rad = 52   # anchor distance from the table center to each seat's slot
        if seat == NORTH:
            return cx - cw // 2, cy - rad - ch // 2
        if seat == SOUTH:
            return cx - cw // 2, cy + rad - ch // 2
        if seat == WEST:
            return cx - rad - cw // 2, cy - ch // 2
        return cx + rad - cw // 2, cy - ch // 2   # EAST

    def _render_narration(self):
        app = self.app
        if self.collecting_winner is not None:
            return  # keep the "collecting..." line from _after_play
        if self.movie_mode:
            if self.movie_page < len(self.narr_pages):
                txt = "Bridge movie  [%d/%d]\n%s" % (
                    self.movie_page + 1, len(self.narr_pages), self.narr_pages[self.movie_page])
            else:
                txt = "End of the bridge movie."
            app._set_narr(txt)
            return
        # during play: show the narration for the current trick group
        page = self.narr_pages[min(self.tricks_played, len(self.narr_pages) - 1)] \
            if self.narr_pages else ""
        app._set_narr(page)


def _trick_winner_local(trick, trump):
    led = trick[0][1].suit
    best_seat, best_rank = trick[0][0], trick[0][1].rank
    for seat, c in trick:
        if c.suit == led and c.rank > best_rank:
            best_rank, best_seat = c.rank, seat
    if trump is not None and led != trump:
        for seat, c in trick:
            if c.suit == trump:
                return seat
    return best_seat


SUIT_ABBR_LOCAL = ["C", "D", "H", "S"]
