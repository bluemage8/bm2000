# Bridge Master 2000 -- Web Edition

[English](README.md) · **[简体中文](README_ZH.md)**

A faithful web rebuild of the desktop `bm2000` build.  Same 5 skill levels and
deals, same game model (you are declarer = South and dummy = North; the computer
plays the East/West defense), same teaching narration, same "collect the trick"
pace, same flashy **DEAL / FAILED** end-of-deal dialog.  The whole app lives on a
fixed **794×547** "window" that is **scaled with CSS `transform: scale()`** to fit
your browser window while keeping its aspect ratio (no stretching / no
letterbox distortion).

The interface is **bilingual (English / 简体中文)** and **auto-switches to your
browser / terminal language** (see [Language](#language--en--中文) below).

## Run it

```
cd web
py server.py            # -> http://127.0.0.1:8321
py server.py 9000       # custom port
```

On first start the server auto-generates `deals.json` from `../winexe/hands` via
`gen_deals.py` (only if missing).  Open the printed URL in a browser.

> You can also regenerate the deal data any time with `py web/gen_deals.py`.

## Files

| file               | purpose                                                        |
|--------------------|----------------------------------------------------------------|
| `server.py`        | stdlib HTTP server: serves the static files + `/api/deals`.   |
| `gen_deals.py`     | parses the 5 levels of deals into `deals.json` (validated).    |
| `deals.json`       | the deal table (generated; not hand-edited).                   |
| `index.html`       | the page: `#stage` holds the TOC and the play view.            |
| `style.css`        | layout + the scale-to-fit `#stage` + the flashy end dialog.    |
| `app.js`           | play engine (mirrors `bm2000/playgame.py`) + canvas rendering + responsive scaling. |
| `selftest.html`    | in-browser smoke test (load deals, play sampled deals, scaling).|

## What scales

* `#stage` is a fixed 794×547 box.  On load and on every window resize,
  `fitStage()` sets `transform: scale(min(100vw/794, 100vh/547, 3))` and centers
  it, so the UI stays proportionally sized at any window size / on phones.
* The green table is a `<canvas>` drawn at the device pixel ratio for crisp text.

## Controls (in-game)

* **Click** a highlighted card in your South/North hand to play it (follow-suit
  is enforced; ruff/discard when void).  The defense opens and plays
  automatically.
* Toolbar: **Replay** (restart the deal), **Take back** (undo last play),
  **Step** (advance one defense card), **Claim** (end after ≥5 tricks),
  **Movie** (roll the expert's narration), **Big/Small** (card size).

## Deployment to 172.16.129.220

Deployed as a nohup background process on the LAN server `172.16.129.220`
(CentOS 7, Python 3.6).  Access it in a browser at **http://172.16.129.220:8321**.

    # start   (binds 0.0.0.0:8321)
    bash /opt/bm2000/start.sh 8321
    # stop
    bash /opt/bm2000/stop.sh

Files live in `/opt/bm2000/`.  `server.out` / `server.err` are the logs.
Notes from the deploy:

* `server.py` was made **Python 3.6-compatible** (the target has 3.6.8): the
  3.7-only `ThreadingHTTPServer` import was replaced with a local
  `ThreadingMixIn + HTTPServer` class and the `from __future__ import
  annotations` line was dropped.
* It binds **0.0.0.0** (not 127.0.0.1) so LAN clients can reach it; host/port
  are configurable via `BM2000_HOST` / `BM2000_PORT` or the argv port.
* Port **8321/tcp** had to be opened in **firewalld** on the target
  (`firewall-cmd --permanent --add-port=8321/tcp`), which was active and
  otherwise blocked the port from the LAN.
* `deals.json` is shipped with the install, so the target does not need
  `winexe/hands` or the Python `bm2000` package -- it is pure static + stdlib.
* This is a **nohup** run (per request), not a systemd service: it will not
  auto-restart after a reboot.  To make it persistent, register a systemd unit or
  add the `start.sh` call to a boot script.

## Language — EN / 中文

The web build shows **English or Simplified Chinese** automatically:

* **Auto-detect** — on load it reads `navigator.language`; a `zh…` value picks
  Chinese, anything else picks English.  So a Chinese-language browser / terminal
  opens the game in Chinese, an English one in English.
* **Manual override** — the **EN / 中文** buttons (top-right) switch at any time;
  the choice is saved in `localStorage` and remembered next visit.
* **URL override** — append `?lang=en` or `?lang=zh` to force a language
  (e.g. `…/?level=1&deal=0&lang=zh`).

The whole UI follows the choice — title bar, level buttons, status line,
seat labels (南/西/北/东), toolbar (Replay/Take back/Step/Claim/Movie/…),
the score strip (墩 / 局况 / 大牌), the narration header, and the end-of-deal
dialog (完成 / 未成, 重新开始 / 显示答案 / 下一副).  Card faces, ranks, suits and
the auction bids stay standard (2–A, ♠♥♦♣, 1NT, 4S, …) in both languages.

## Notes

* 5 records in the original `winexe/hands` data have corrupt `md` values that
  don't form a legal 52-card board; `gen_deals.py` skips them (the desktop build
  does too).  530 playable deals remain.
* The web build's defense uses the same defensive conventions as the desktop
  build (see `../analysis/GAPS.md`), not a full adversarial search.
* Each card is given a unique internal id so two cards that legitimately share a
  rank + suit (possible in the data) are still treated as distinct; without this
  such boards can't be completed.
