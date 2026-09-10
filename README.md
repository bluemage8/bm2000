# BridgeMaster2000 (bm2000) -- Bridge Master 2000

[**简体中文 / Chinese**](README_ZH.md)  ·  English

[![Build Android APK](https://github.com/bluemage8/bm2000/actions/workflows/build-apk.yml/badge.svg)](https://github.com/bluemage8/bm2000/actions/workflows/build-apk.yml)

A faithful re-implementation of **Bridge Master 2000** — a classic Windows
"learn to play bridge as declarer" teaching program.  It includes **three builds**
that share one verified bridge engine:

* **A desktop build** (Python 3 + Tkinter) launched from [`run.py`](run.py).
* **A browser build** (vanilla JS + canvas) served by [`web/server.py`](web/server.py),
  which scales the original 794×547 "window" to fit your browser.
* **An Android build** (Kotlin + WebView) in [`android/`](android/), built
  automatically by **GitHub Actions** — see [Android app](#android-app) below.

Same 5 skill levels, same ~530 deals, same game model, same expert narration,
same flashy **DEAL / FAILED** end-of-deal dialog.

> **Scope / legal note.** This project re-implements the game from a study of its
> behaviour and ships the *deal data* and *help file* extracted from the original
> so the games are faithful.  The original **`bm2000.exe` binary is NOT included**
> here — it is proprietary and is deliberately excluded.  The data in
> [`winexe/hands`](winexe/hands) is provided only so the included code can run
> and be verified against the original.

---

## What it is

You play **declarer = South** and **dummy = North**.  The computer plays the
**defence = East + West** (West opens the lead).  Your only objective is to take
at least the number of tricks required to make your contract.  Overtricks do not
matter.

* You play **both** the North and South hands.
* The computer plays the East/West defence automatically using standard
  defensive conventions (fourth-best from 4+, high from a doubleton, low from a
  bare three-card suit; follow-suit; ruff when sensible).
* **Follow-suit is enforced** for everyone; the on-lead hand is the only one you
  may play from (all other cards are not clickable / not highlighted).
* You may **claim** the contract after 5 tricks, roll the expert
  **"Bridge movie"** narration, step through, or **take back** your last play.

---

## Repository layout

```
.
├── run.py                  # desktop entry point (Tkinter GUI)
├── bm2000/                 # shared Python package -- the one real engine
│   ├── cards.py            #   Card / Deal model + validation
│   ├── script.py           #   .LIN solution/bidding parser
│   ├── levels.py           #   level index reader (winexe/hands/<n>)
│   ├── playgame.py         #   interactive trick-by-trick play engine
│   ├── replay.py           #   fast headless auto-play (for tests)
│   ├── bidding.py          #   bidding / contract + declarer determination
│   ├── contract.py         #   contract semantics: tricks needed (level+6),
│   │                       #     game / slam detection, scoring breakdown
│   ├── engine.py           #   higher-level deal runner
│   ├── gui.py              #   the Tkinter GUI (TOC + play view + dialogs)
│   └── sound.py            #   tiny sound-effect stub
├── web/                    # the browser build
│   ├── server.py           #   stdlib HTTP server (static + /api/deals)
│   ├── gen_deals.py        #   generates web/deals.json from winexe/hands
│   ├── deals.json          #   the pre-built deal table (530 deals)
│   ├── index.html          #   the page (#stage holds TOC + play view)
│   ├── style.css           #   layout + scale-to-fit + flashy end dialog
│   ├── app.js              #   play engine + canvas rendering + scaling
│   ├── selftest.html       #   in-browser smoke test (loads + plays deals)
│   └── README.md           #   web-specific usage + deployment notes
├── android/                # Android app (Kotlin + WebView shell)
│   ├── app/src/main/assets #   bundled web edition + deals.json/deals.js
│   ├── app/src/main/java/.../MainActivity.kt   # WebView shell + data bridge
│   └── README.md           #   Android build / install notes
├── .github/workflows/      # GitHub Actions: build the APK (see "Android app")
└── winexe/                 # data extracted from the original (no .exe)
    ├── hands/              #   the 5 levels of deal data (the games)
    └── BM2000.HLP          #   the original program's help/manual file
```

---

## Requirements

* **Desktop build:** Python **3.8+** with `tkinter` (standard on most installs;
  on Linux: `sudo apt install python3-tk`).
* **Web build:** Python **3.6+** (stdlib only — no third-party packages) **or**
  any static file server.  A modern browser (Chrome/Edge/Firefox) to play.

No third-party Python dependencies are required by either build that ships here.

---

## Running the desktop build

```bash
cd <this repo>

# launch the Tkinter GUI (splash → table of contents → pick a deal)
python run.py

# open a specific level / deal directly
python run.py 1 A1

# just list the levels and their deals (no GUI)
python run.py list
```

`run.py` looks for the deal data in `./winexe/hands` (included here) and for the
help in `./winexe/BM2000.HLP`.

### Desktop controls (in the play screen)

| Toolbar button | Action |
|----------------|--------|
| First / Prev / Next / Last | Jump to first / previous / next / last deal |
| Replay deal | Restart the current deal from scratch |
| Step | Play the next (automatic defence) card |
| Take back | Undo your last play |
| Claim | Declare the contract finished (allowed after ≥5 tricks) |
| Movie / 1st / Prev / Next / Last | Open the expert "bridge movie" and page through it |
| Big / Small | Toggle big / small card size |
| Show / Hide | Toggle whether played cards stay visible |
| Sound on/off | Toggle sound effects |
| Help | Open the program's help |

Click a **highlighted** card in your South or North hand to play it (only the
on-lead hand's legal cards are playable).

---

## Running the web build

The web build needs **no installation** — it is static files plus a tiny stdlib
server that also serves the deal table at `/api/deals`.

```bash
cd web

# start on the default port 8321, bound to 0.0.0.0 (reachable on the LAN)
python server.py            # -> http://<your-ip>:8321  (localhost also works)

# or a custom port
BM2000_PORT=9000 python server.py
# or
python server.py 9000
```

Then open **http://localhost:8321** (or **http://<server-ip>:8321**) in a
browser.  The page auto-scales the 794×547 window to fit the browser and keeps
its aspect ratio at any window size / on a phone.

> `deals.json` is **already generated** and committed, so the web build works
> out of the box.  To regenerate it (e.g. after changing data):
>
> ```bash
> python web/gen_deals.py    # rewrites web/deals.json from ../winexe/hands
> ```

### Web controls

* **Click** a highlighted card in your South/North hand to play it (only the
  on-lead hand's legal cards are playable; follow-suit enforced; ruff/discard
  when void).  The defence opens and plays automatically.
* Toolbar: **Replay**, **Take back**, **Step**, **Claim**, **Movie** (plays the
  expert narration), **Big/Small**.
* End of deal: a flashing **DEAL** (made) / **FAILED** (down) dialog with your
  score, and **Restart / Show answer / Next deal** buttons.

### In-browser self-test

Open `web/selftest.html` (it is served at
**http://localhost:8321/selftest.html**).  It loads all 530 deals, plays a
sample of them to completion, and checks the responsive scaling.  It prints
**`RESULT: ALL PASS`** when the data and engine are healthy.

---

## Android app

The Android build (`android/`) is a native **Kotlin + WebView** shell around the
same web edition: the WebView loads the bundled `index.html` / `app.js` /
`style.css`, the deal table is packaged offline (`assets/deals.json` + a
`deals.js` preloader fallback), and the 794×547 board auto-scales to the
screen (landscape).  Gameplay is identical to the web build.

### Getting the APK (no build required)

The APK is built automatically by **GitHub Actions** (`.github/workflows/build-apk.yml`):

* **Every push to `main`** produces a fresh debug APK, available as the
  `bm2000-debug` artifact on the run's page
  ([Actions](https://github.com/bluemage8/bm2000/actions)).
* **Pushing a version tag** (e.g. `git tag v1.0 && git push origin v1.0`)
  creates a **GitHub Release** with the APK attached — download it from
  [Releases](https://github.com/bluemage8/bm2000/releases).

To install on a phone: copy the APK to the device and open it (allow
"install from unknown sources" when prompted).  Requires Android 7.0+ (API 24).

### Building it yourself

You do **not** need the original WSL toolchain — a standard JDK 17 + Android
SDK is enough.  The repo does not ship the Gradle wrapper jar, so invoke the
system `gradle` (or Android Studio):

```bash
cd android

# one-time: if you don't have a Gradle wrapper jar, generate it (needs gradle on PATH)
gradle wrapper --gradle-version 8.7

# build a debug APK (installable as-is)
gradle :app:assembleDebug
#   -> app/build/outputs/apk/debug/app-debug.apk

# or open the android/ folder in Android Studio and Run to a device
```

Prereqs: **JDK 17**, **Android SDK** (compileSdk 34), **Gradle 8.7+**.
`applicationId` is `com.bm2000.bridge`; `minSdk 24` / `targetSdk 34`.

> A **release** (Play-store / signed) build needs a signing key; configure
> `signingConfigs` in `app/build.gradle` or use Android Studio's
> *Build ▸ Generate Signed APK*.  The CI build ships a debug-signed APK.

Full details live in [`android/README.md`](android/README.md).

---

## The game model (both builds)

The desktop and web builds both delegate to the same rules, so they behave
identically:

* **Trick winner** — the highest trump of that trick if any trump was played on
  a non-trump lead; otherwise the highest card of the led suit.
* **Legal play** — you must follow the led suit if you hold it; otherwise you
  may ruff (play a trump) or discard.
* **Lead rotation** — the winner of a trick leads the next; the human may play
  only from whichever of North/South is actually on lead.
* **Result** — the contract is *made* if North+South take at least
  **level + 6** tricks (a 1-level contract needs 7, a 4-level high-major 10,
  a 7-level grand slam all 13); otherwise it is *down*.  The end-of-deal
  dialog scores the result: trick points (minors 20/level, majors 30/level,
  NT 40 + 30·(level−1)), a **game** bonus when the contract reaches the game
  line (3NT / 4♥ / 4♠ / 5♣ / 5♦), **small-slam** (6-level) and **grand-slam**
  (7-level) bonuses, and an undertrick penalty when defeated.

The defensive AI uses the same **conventions** in both builds (it is not a deep
adversarial search).  This is documented as a known, intentional simplification.

---

## Deploying the web build to a server

There is a nohup launcher at `web/` for a Linux host.  Minimum steps on a
Python 3.6+ box:

```bash
# 1. copy the web/ folder (it is self-contained: static + deals.json + server.py)
scp -r web/* user@host:/opt/bm2000/

# 2. on the host, start it bound to 0.0.0.0:8321
cd /opt/bm2000
BM2000_HOST=0.0.0.0 nohup python3 server.py 8321 >> server.out 2>> server.err &

# 3. allow the port through any firewall, e.g. firewalld (CentOS):
sudo firewall-cmd --permanent --add-port=8321/tcp && sudo firewall-cmd --reload
```

Then reach it from the LAN at **http://<host-ip>:8321**.  For a
reboot-survivable setup, register it as a systemd unit instead of nohup.  Full
deployment notes live in [`web/README.md`](web/README.md).

> `web/server.py` is written to run on Python **3.6+** (it backports
> `ThreadingHTTPServer` and avoids 3.7-only syntax), and binds `0.0.0.0` by
> default so LAN clients can reach it (`BM2000_HOST` / `BM2000_PORT` to
> override).

---

## Verifying the re-implementation

The shared engine is exercised by automated checks:

* **52-card conservation** — a full auto-play of any deal ends with all 52
  cards dealt into 13 tricks and every hand at 0.
* **Follow-suit / on-lead restriction** — only legal cards of the on-lead hand
  are accepted; off-lead and off-suit plays are rejected.
* **Trick-winner parity** — randomised tricks were checked against an
  independent reference (100 % match).
* **Web self-test** — `web/selftest.html` replays a sample of all 530 deals
  in the browser and asserts the invariants.

---

## Data notes

* The 5 skill levels come from `winexe/hands/<1..5>/{Index,Data}`.
* 5 records in the original data have corrupt `md` (master-deal) values that do
  not form a legal 52-card board; both builds **skip** those records
  automatically, leaving **530 playable deals**
  (Level 1: 182, L2: 95, L3: 94, L4: 94, L5: 65).
* The `.LIN` filenames are recycled across levels (e.g. `A1.LIN` exists in every
  level but holds a different hand), so deals are addressed by a
  `<series>-<n>` code (A-1, B-12, …) rather than by filename.

---

## License

This is a **study / re-implementation** for personal and educational use.  It
does not include the original proprietary executable.  The deal data and help
file are provided only to make the included code runnable and verifiable.
Respect the original software's rights — do not redistribute the original
`bm2000.exe`.
