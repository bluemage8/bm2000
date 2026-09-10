/* Bridge Master 2000 -- web edition.
 *
 * Fixed 794x547 stage scaled with CSS transform:scale() to fit the browser
 * window while preserving aspect ratio.  The play engine below mirrors the
 * desktop build (bm2000/playgame.py): you play South + North, the computer
 * plays East + West; follow-suit is enforced; the defense uses defensive
 * conventions.  Trick cards sit on fixed per-seat anchors (no sliding) and a
 * short "collection" hold highlights the winner.
 */
"use strict";

// ---------------------------------------------------------------------------
//  constants (mirror bm2000/cards.py)
// ---------------------------------------------------------------------------
const SOUTH = 0, WEST = 1, NORTH = 2, EAST = 3;
const SEAT_NAMES = ["South", "West", "North", "East"];
const RANK_CHARS = {14:"A",13:"K",12:"Q",11:"J",10:"T",9:"9",8:"8",7:"7",6:"6",5:"5",4:"4",3:"3",2:"2"};
const SUIT_ABBR = ["c","d","h","s"];
const SUIT_SYM  = ["\u2663","\u2666","\u2665","\u2660"];
const SUIT_RED  = [false, true, true, false];     // d,h red
const LEVEL_COLORS = ["#cc2222","#22aa22","#2244cc","#ccaa00","#aa22aa"];
const FELT = "#0b5d2e", FELT_EDGE = "#063d1e";

// ---------------------------------------------------------------------------
//  i18n -- auto-detected from the browser/terminal language, with a manual
//  EN / 中文 override (saved to localStorage and reflected in the URL ?lang=)
// ---------------------------------------------------------------------------
const I18N = {
  en: {
    pageTitle: "Bridge Master 2000",
    south: "South", west: "West", north: "North", east: "East",
    seatDummy: "NORTH  (dummy, you)", seatDealer: "SOUTH  (declarer, you)",
    seatDef: "  (defense)",
    level: "Level",
    loading: "Loading deals…",
    failedLoad: "Failed to load deals",
    tocStatus: (n) => "Lv " + n + ": ",              // + " 530 deals. Click a deal to play."
    tocStatusDeals: " deals. Click a deal to play.",
    pass: "Pass",
    replay: "Replay", takeback: "Take back", step: "Step", claim: "Claim",
    movie: "Movie", bigBtn: "Big", smallBtn: "Small",
    by: "by", passout: "Pass out", vuln: "Vuln", hcp: "HCP", trick: "Trick",
    win: "WIN",
    takes: (seat, side) => seat + " takes the trick (" + side + ") — collecting…",
    yourSide: "your side", defense: "the defense",
    movieCap: (c, t) => "Bridge movie  [" + (c + 1) + "/" + t + "]",
    movieEnd: "End of the bridge movie.",
    englishNote: "(Expert narration is provided in English.)",
    dealWord: "DEAL", failWord: "FAILED", passWord: "PASS",
    endScoreNeeds: "contract needs",
    passOutSub: "Pass out — no contract reached.",
    madeSub: (txt, won, lv) => txt + " made  (" + won + " of " + lv + " tricks won)",
    downSub: (txt, won, lv) => txt + " down  (" + won + " of " + lv + " tricks won)",
    expert: "Expert rating",
    restart: "Restart deal", showAnswer: "Show answer", nextDeal: "Next deal",
  },
  zh: {
    pageTitle: "桥牌大师 2000",
    south: "南", west: "西", north: "北", east: "东",
    seatDummy: "北  (明手·你)", seatDealer: "南  (庄·你)",
    seatDef: " (防守)",
    level: "第",
    loading: "正在加载牌局…",
    failedLoad: "加载牌局失败",
    tocStatus: (n) => "第" + n + "级：",
    tocStatusDeals: " 副。点击一副牌开始。",
    pass: "Pass",
    replay: "重放", takeback: "悔棋", step: "单步", claim: "摊牌",
    movie: "讲解", bigBtn: "放大", smallBtn: "缩小",
    by: "由", passout: "Pass", vuln: "局况", hcp: "大牌", trick: "墩",
    win: "赢",
    takes: (seat, side) => seat + " 拿下这墩（" + side + "）— 收集中…",
    yourSide: "我方", defense: "防守方",
    movieCap: (c, t) => "桥牌讲解  [" + (c + 1) + "/" + t + "]",
    movieEnd: "讲解结束。",
    englishNote: "（专家讲解以英文提供。）",
    dealWord: "完成", failWord: "未成", passWord: "Pass",
    endScoreNeeds: "需",
    passOutSub: "Pass — 未叫成定约。",
    madeSub: (txt, won, lv) => txt + " 完成（拿到 " + won + " 墩，需 " + lv + " 墩）",
    downSub: (txt, won, lv) => txt + " 未成（拿到 " + won + " 墩，需 " + lv + " 墩）",
    expert: "专家评分",
    restart: "重新开始", showAnswer: "显示答案", nextDeal: "下一副",
  },
};

let App = {};    // declared later (const App = {...}); i18n just needs a home for `lang`

// auto-detect the locale.  Priority: explicit ?lang=  >  saved choice
// (localStorage)  >  browser language.  Optional overrides (urlLang / storage /
// navLang) let tests / headless shots pin the result; with none supplied it
// reads the live page.  (URL always wins, so a shared link forces its language.)
function detectLocale(urlLang, storage, navLang) {
  // 1. explicit ?lang= (or the test override) wins
  if (urlLang === undefined) {
    try { urlLang = new URLSearchParams(location.search).get("lang"); } catch (e) {}
  }
  if (urlLang) {
    const k = String(urlLang).toLowerCase();
    // accept full locale tags ("en-US", "zh-CN") as well as bare codes ("en")
    if (I18N[k]) return k;
    const sub = k.split("-")[0];
    if (I18N[sub]) return sub;
  }
  // 2. saved choice from a previous session
  if (storage === undefined) {
    try { storage = localStorage.getItem("bm2000.lang"); } catch (e) {}
  }
  if (storage && I18N[storage]) return storage;
  // 3. the browser / terminal language (auto-switch)
  const nav = (navLang || navigator.language || navigator.userLanguage || "en").toLowerCase();
  return nav.indexOf("zh") === 0 ? "zh" : "en";
}
function lang() { return I18N[App.lang] || I18N.en; }
// tAt(key, loc) resolves `key` in an explicit locale -- handy for tests/shots
function tAt(key, loc) { const d = I18N[loc] || I18N.en; return d[key]; }
// t(key, ...args) resolves a string; if the entry is a function (a template) the
// args are passed through, e.g. t("over", 3, 10, 7).
function t(key) {
  const v = lang()[key];
  if (typeof v === "function") { var a = Array.prototype.slice.call(arguments, 1); return v.apply(null, a); }
  return v !== undefined ? v : key;
}
// a function-valued string that also needs a fallback param (e.g. t("tocStatus", 5))
function tf(key) { var a = Array.prototype.slice.call(arguments, 0); return t.apply(null, a); }
const seatLabel = (i) => [t("south"), t("west"), t("north"), t("east")][i];
function setLocale(l, persist) {
  if (!I18N[l]) return;
  App.lang = l;
  if (persist !== false) { try { localStorage.setItem("bm2000.lang", l); } catch (e) {} }
  const e = $("langEn"); if (e) e.classList.toggle("on", l === "en");
  const z = $("langZh"); if (z) z.classList.toggle("on", l === "zh");
  if (App.data && !App.game) { buildTOC(); selectLevel(App.curLevel || 1); }
  render();
}

// ---------------------------------------------------------------------------
//  small DOM helpers
// ---------------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const el = (tag, cls, html) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};

// ---------------------------------------------------------------------------
//  responsive scaling: scale the fixed 794x547 stage to fit the window
// ---------------------------------------------------------------------------
const STAGE_W = 794, STAGE_H = 547;
function fitStage() {
  const stage = $("stage");
  const vw = window.innerWidth, vh = window.innerHeight;
  const s = Math.min(vw / STAGE_W, vh / STAGE_H, 3);   // cap upscale at 3x
  stage.style.transform = "scale(" + s + ")";
  return s;
}

// ---------------------------------------------------------------------------
//  play engine (mirrors bm2000/playgame.py)
// ---------------------------------------------------------------------------
function trumpOf(contract) {
  if (!contract) return null;
  return (contract.suit === "c" || contract.suit === "d" ||
          contract.suit === "h" || contract.suit === "s")
    ? { c: 0, d: 1, h: 2, s: 3 }[contract.suit] : null;
}

// NOTE: cards are objects with { r, s } (rank, suit) -- see gen_deals.py /
// deals.json.  (The *contract* object separately uses .suit as a letter string;
// that is handled in trumpOf.)  Do NOT use card.suit / card.rank here.
function trickWinner(trick, trump) {
  const led = trick[0].card.s;
  let bestSeat = trick[0].seat, bestRank = trick[0].card.r;
  const trumps = [];
  for (const p of trick) {
    if (p.card.s === trump) trumps.push([p.seat, p.card.r]);
  }
  if (trumps.length && led !== trump) {
    trumps.sort((a, b) => b[1] - a[1]);
    return trumps[0][0];
  }
  for (const p of trick) {
    if (p.card.s === led && p.card.r > bestRank) {
      bestRank = p.card.r; bestSeat = p.seat;
    }
  }
  return bestSeat;
}

function sideOf(seat) { return (seat === SOUTH || seat === NORTH) ? 0 : 1; }

function legalCards(hand, trick) {
  if (!trick.length) return hand.slice();
  const led = trick[0].card.s;
  const follow = hand.filter((c) => c.s === led);
  return follow.length ? follow : hand.slice();
}

function openingLead(hand, trump) {
  const suits = {};
  hand.forEach((c) => (suits[c.s] = suits[c.s] || []).push(c));
  for (const k in suits) suits[k].sort((a, b) => a.r - b.r);
  const score = (suit) => {
    const n = suit.length;
    const top3 = suit.slice(-3).map((c) => c.r);
    let seq = 1;
    for (let i = 0; i < top3.length - 1; i++)
      if (top3[i + 1] === top3[i] + 1) seq++;
    return [n >= 4 ? 1 : 0, n, seq, -suit[0].r];
  };
  const arr = Object.values(suits);
  arr.sort((a, b) => (score(b)[0] - score(a)[0]) || (score(b)[1] - score(a)[1]) ||
                     (score(b)[2] - score(a)[2]) || (score(a)[3] - score(b)[3]));
  const best = arr[0];
  const n = best.length;
  if (n === 2) return best[n - 1];
  if (n === 3) return best[0];
  return best.length >= 4 ? best[n - 4] : best[0];
}

function defenseFollow(seat, hand, trick, trump) {
  if (!trick.length) return openingLead(hand, trump);
  const led = trick[0].card.s;
  const follow = hand.filter((c) => c.s === led);
  const trumpHand = trump === null ? [] : hand.filter((c) => c.s === trump);
  if (follow.length) {
    const maxLed = Math.max(0, ...trick.filter((p) => p.card.s === led).map((p) => p.card.r));
    const winners = follow.filter((c) => c.r > maxLed && led === trump);
    const pool = winners.length ? winners : follow;
    pool.sort((a, b) => a.r - b.r);
    return pool[0];
  }
  if (trump !== null && led !== trump && trumpHand.length) {
    const played = trick.filter((p) => p.card.s === trump).map((p) => p.card.r);
    if (!played.length) return [...trumpHand].sort((a, b) => a.r - b.r)[0];
  }
  if (trumpHand.length) return [...trumpHand].sort((a, b) => a.r - b.r)[0];
  return [...hand].sort((a, b) => a.r - b.r || a.s - b.s)[0];
}

// a card is uniquely identified by its _id (two cards can share rank+suit in
// the data, so r+s alone is NOT a safe identity).
const C = (r, s) => ({ r, s, _id: Math.random().toString(36).slice(2) });
function sameCard(a, b) { return !!a && !!b && (a._id !== undefined ? a._id === b._id : a.r === b.r && a.s === b.s); }

class Game {
  constructor(hands, contract) {
    // hands: [ [ {r,s} x13 ] x4 ] already in display order; deep-copy.
    // Each card gets a unique _id so two cards that share rank+suit (possible
    // in the data) are still distinct objects -- identity is by _id, not r+s.
    this.hands = hands.map((h) => h.map((c) => ({ r: c.r, s: c.s, _id: Math.random().toString(36).slice(2) })));
    this.contract = contract;
    this.trump = trumpOf(contract);
    this.leader = WEST;           // the defense leads into dummy
    this.trick = [];
    this.tricks = [];
    this.wonNS = 0;
    this.done = false;
  }
  get toPlay() { return this.done ? null : (this.leader + this.trick.length) % 4; }
  get tricksPlayed() { return this.tricks.length; }
  get score() { const lvl = this.contract ? this.contract.level : 0; return [this.wonNS, lvl]; }
  get needs() { return this.contract ? this.contract.level : 0; }
  // Bridge Master stops as soon as the result is decided (HLP: play is
  // interrupted before all 13 tricks once "the defenders win enough tricks so
  // that it is impossible for declarer to win the optimum number of tricks,
  // OR if declarer has reached the goal of the contract").  So end when:
  //   * North+South already took `needs` tricks  -> contract made, stop;
  //   * even winning every remaining trick can no longer reach `needs` -> down;
  //   * all 13 tricks are played.
  get decided() {
    const need = this.needs;
    if (need <= 0) return this.tricks.length >= 13;
    if (this.wonNS >= need) return true;
    const remaining = 13 - this.tricks.length;
    if (this.wonNS + remaining < need) return true;   // can no longer make it
    return false;
  }
  legal() {
    const seat = this.toPlay;
    if (seat === null) return [];
    return legalCards(this.hands[seat], this.trick);
  }
  play(card) {
    if (this.done) return null;
    const seat = this.toPlay;
    if (!this.hands[seat].some((c) => sameCard(c, card))) return null;
    if (!legalCards(this.hands[seat], this.trick).some((c) => sameCard(c, card))) return null;
    this.hands[seat] = this.hands[seat].filter((c) => !sameCard(c, card));
    const entry = { seat, card };
    this.trick.push(entry);
    if (this.trick.length === 4) {
      const winner = trickWinner(this.trick, this.trump);
      this.tricks.push(this.trick);
      if (sideOf(winner) === 0) this.wonNS++;
      this.leader = winner;
      this.trick = [];
      if (this.tricks.length === 13 || this.decided) this.done = true;
      return winner;
    }
    return null;
  }
  defenseStep() {
    const seat = this.toPlay;
    if (seat === null || seat === SOUTH || seat === NORTH) return null;
    const card = defenseFollow(seat, this.hands[seat], this.trick, this.trump);
    // resolve to the actual hand object (unique id) so play() updates the right one
    const real = this.hands[seat].find((c) => sameCard(c, card)) || card;
    return this.play(real);
  }
}

// ---------------------------------------------------------------------------
//  card drawing on canvas
// ---------------------------------------------------------------------------
function drawCard(ctx, x, y, w, h, card, faceUp, dim, highlight) {
  if (!faceUp) {
    ctx.fillStyle = "#3355aa"; ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = "#101a40"; ctx.lineWidth = 1; ctx.strokeRect(x, y, w, h);
    ctx.strokeStyle = "#5a79c8"; ctx.strokeRect(x + 2, y + 2, w - 4, h - 4);
    return;
  }
  ctx.fillStyle = dim ? "#c9c9c9" : (highlight ? "#fff3b0" : "#ffffff");
  ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = dim ? "#7a7a7a" : (highlight ? "#c9a200" : "#404040");
  ctx.lineWidth = 1; ctx.strokeRect(x, y, w, h);
  const color = dim ? "#b9b9b9" : (SUIT_RED[card.s] ? "#c01818" : "#101010");
  const r = RANK_CHARS[card.r], sym = SUIT_SYM[card.s];
  const fs = Math.max(9, Math.min(18, Math.floor(w / 2), Math.floor(h / 3)));
  ctx.fillStyle = color;
  ctx.font = "bold " + fs + "px Consolas, monospace";
  ctx.textBaseline = "top"; ctx.textAlign = "left";
  ctx.fillText(r, x + 2, y + 2);
  ctx.font = (fs - 1) + "px Consolas, monospace";
  ctx.fillText(sym, x + 2, y + 2 + fs);
  ctx.font = "bold " + fs + "px Consolas, monospace";
  ctx.textAlign = "right";
  ctx.fillText(r, x + w - 2, y + 2);
  ctx.font = (fs - 1) + "px Consolas, monospace";
  ctx.textAlign = "left";
  ctx.fillText(sym, x + 2, y + 2 + fs);
}

function drawBack(ctx, x, y, w, h) {
  ctx.fillStyle = "#2f4f9e"; ctx.fillRect(x, y, w, h);
  ctx.strokeStyle = "#101a40"; ctx.lineWidth = 1; ctx.strokeRect(x, y, w, h);
  ctx.strokeStyle = "#8fa8e0";
  ctx.beginPath(); ctx.arc(x + w / 2, y + h / 2, 3, 0, 7); ctx.stroke();
}

// ---------------------------------------------------------------------------
//  app state
// ---------------------------------------------------------------------------
App = {
  lang: detectLocale(),
  data: null,
  curLevel: 0,
  curDeal: -1,
  results: {},          // "level:idx" -> "made" | "down"
  game: null,
  collectingWinner: null,
  collectMs: 1100,
  movieMode: false,
  moviePage: 0,
  narrPages: [],
  undoStack: [],
  board: null,
  ctx: null,
  big: true,
};

// ---------------------------------------------------------------------------
//  TOC
// ---------------------------------------------------------------------------
function colorOf(level) { return LEVEL_COLORS[(level - 1) % LEVEL_COLORS.length]; }

function buildTOC() {
  const lvcol = $("lvcol");
  lvcol.innerHTML = "";
  App.data.levels.forEach((lv) => {
    const b = el("button", "lvbtn", t("level") + lv.level);
    b.style.background = colorOf(lv.level);
    b.onclick = () => selectLevel(lv.level);
    lvcol.appendChild(b);
  });
}

function selectLevel(level) {
  App.curLevel = level;
  const lv = App.data.levels.find((l) => l.level === level);
  const rows = $("dealRows");
  rows.innerHTML = "";
  // list deals in deck order, labelled "<series>-<n>" (A-1, A-2, ... B-1, ...)
  // exactly like the original.  Deal n is always deals[n-1].
  lv.deals.forEach((d, i) => {
    // label as "<series>-<n>" (e.g. A-1, B-12), matching the original's deal
    // codes.  The raw .LIN filenames are recycled across levels and don't
    // uniquely identify a deal, so we use the per-level index instead.
    const code = lv.series + "-" + (i + 1);
    const row = el("li", "deal-row",
      '<span class="nm">' + code + '</span>' +
      '<span class="ct">' + (d.contract ? d.contract.text : t("pass")) + '</span>' +
      '<span class="mk"></span>');
    const key = level + ":" + i;
    const r = App.results[key];
    if (r === "made") { row.classList.add("made"); row.querySelector(".mk").textContent = "\u2713"; }
    else if (r === "down") { row.classList.add("down"); row.querySelector(".mk").textContent = "\u2717"; }
    row.onclick = () => { row.className = "deal-row sel " + (r || ""); playDeal(level, i); };
    rows.appendChild(row);
  });
  setTocVisible(true);
  $("status").textContent = tf("tocStatus", level) + lv.deals.length + t("tocStatusDeals");
}

function setTocVisible(v) {
  $("toc").classList.toggle("hidden", !v);
  $("play").classList.toggle("hidden", v);
}

// ---------------------------------------------------------------------------
//  play
// ---------------------------------------------------------------------------
function playDeal(level, idx) {
  const lv = App.data.levels.find((l) => l.level === level);
  const d = lv.deals[idx];
  App.curLevel = level;
  App.curDeal = idx;
  App.game = new Game(d.hands, d.contract);
  App.curDealData = d;
  App.collectingWinner = null;
  App.movieMode = false;
  App.moviePage = 0;
  App.undoStack = [];
  App.narrPages = buildNarrPages(d.captions);

  // bidding strip: auction + contract + vuln + HCP
  $("playStrip").innerHTML = stripHtml(0, 0, 1);
  buildToolbar();
  setTocVisible(false);
  render();
  kickedOff();
}

function vulnText(code) {
  code = (code || "").trim();
  const t = {
    "010": "EW", "0200": "NS", "020": "NS",
    "100": "WE", "101": "NW", "110": "EW",
    "200": "NS", "202": "EW", "300": "EW", "400": "NS",
  };
  return t[code] || code;
}

function buildNarrPages(captions) {
  // split the deal's captions into pages (one per caption for simplicity)
  return captions.filter((c) => c && c.trim());
}

function buildToolbar() {
  const tb = $("toolbar");
  tb.innerHTML = "";
  const mk = (txt, fn, on) => {
    const b = el("button", on ? "on" : "", txt);
    b.onclick = fn;
    tb.appendChild(b);
    return b;
  };
  mk(t("replay"), () => { const g = App.game; g = resetGame(); }, false);
  mk(t("takeback"), undo, false);
  mk(t("step"), stepForward, false);
  mk(t("claim"), claim, false);
  const mv = mk(t("movie"), toggleMovie, App.movieMode); mv.id = "tbMovie";
  const bs = mk(App.big ? t("smallBtn") : t("bigBtn"), toggleCardSize, false); bs.id = "tbBig";
}

function resetGame() {
  const d = App.curDealData;
  App.game = new Game(d.hands, d.contract);
  App.collectingWinner = null;
  App.movieMode = false;
  App.moviePage = 0;
  App.undoStack = [];
  render();
  kickedOff();
}

function pushUndo() {
  App.undoStack.push({
    hands: App.game.hands.map((h) => h.map((c) => ({ ...c }))),
    leader: App.game.leader,
    trick: App.game.trick.map((p) => ({ seat: p.seat, card: { ...p.card } })),
    wonNS: App.game.wonNS,
    done: App.game.done,
  });
}

function undo() {
  const u = App.undoStack.pop();
  if (!u) return;
  App.game.hands = u.hands;
  App.game.leader = u.leader;
  App.game.trick = u.trick;
  App.game.wonNS = u.wonNS;
  App.game.done = u.done;
  App.collectingWinner = null;
  render();
}

function stepForward() {
  if (App.movieMode) return;
  advance();
}

function claim() {
  if (App.game.tricksPlayed >= 5) showEndDialog();
  // else: claim is only allowed after 5 tricks (faithful to the original)
}

function toggleCardSize() {
  App.big = !App.big;
  const bs = $("tbBig");   // relabel the Big/Small button
  if (bs) bs.textContent = App.big ? t("smallBtn") : t("bigBtn");
  render();
}

function toggleMovie() {
  App.movieMode = !App.movieMode;
  if (App.movieMode)   App.moviePage = 0;
  render();
  movieBtn();
  if (App.movieMode) movieAutoNext();
}
const movieBtn = () => { const b = $("tbMovie"); if (b) b.classList.toggle("on", App.movieMode); };

function movieAutoNext() {
  if (!App.movieMode) return;
  setTimeout(() => {
    if (!App.movieMode) return;
    if (App.moviePage < App.narrPages.length) App.moviePage++;
    render();
    movieAutoNext();
  }, 2500);
}

// ---------------------------------------------------------------------------
//  progression
// ---------------------------------------------------------------------------
function kickedOff() {
  App.collectingWinner = null;
  if (!App.movieMode && App.game.toPlay !== null &&
      (App.game.toPlay === EAST || App.game.toPlay === WEST)) {
    setTimeout(advance, 420);
  }
}

function advance() {
  if (App.collectingWinner !== null || App.game.done) return;
  const seat = App.game.toPlay;
  if (seat === null) return;
  if (seat === EAST || seat === WEST) {
    pushUndo();
    App.game.defenseStep();
    afterPlay();
  }
}

function afterPlay() {
  render();
  if (App.game.done) { showEndDialog(); return; }
  const justClosed = (App.game.trick.length === 0) && App.game.tricks.length > 0;
  if (justClosed) {
    App.collectingWinner = lastTrickWinner();
    setNarr(collectedLine());
    render();
    setTimeout(finishCollect, App.collectMs);
    return;
  }
  const nxt = App.game.toPlay;
  if (nxt === EAST || nxt === WEST) setTimeout(advance, 420);
}

function lastTrickWinner() {
  const t = App.game.tricks[App.game.tricks.length - 1];
  return t ? trickWinner(t, App.game.trump) : null;
}

function collectedLine() {
  const w = lastTrickWinner();
  if (w === null) return "";
  const side = (w === SOUTH || w === NORTH) ? t("yourSide") : t("defense");
  return t("takes", seatLabel(w), side);
}

function finishCollect() {
  App.collectingWinner = null;
  if (App.game.done) return;
  if (App.game.toPlay === EAST || App.game.toPlay === WEST)
    setTimeout(advance, 240);
}

function playCard(indexInHand, seat) {
  if (App.collectingWinner !== null || App.game.done) return;
  if (seat !== SOUTH && seat !== NORTH) return;
  if (seat !== App.game.toPlay) return;
  const hand = App.game.hands[seat];
  const target = hand[indexInHand];
  if (!target) return;
  if (!legalCards(hand, App.game.trick).some((c) => sameCard(c, target))) return;
  pushUndo();
  App.game.play(target);
  afterPlay();
}

// ---------------------------------------------------------------------------
//  rendering
// ---------------------------------------------------------------------------
function dims() {
  const big = App.big;
  const cw = big ? 34 : 24, ch = big ? 46 : 34, gap = big ? 3 : 2;
  return [cw, ch, gap];
}
function playDims() {
  const big = App.big;
  return big ? [40, 56, 4] : [28, 40, 2];
}

function handX(seat, i, n, w, d) {
  const [cw, , gap] = d || dims();
  const total = n * cw + (n - 1) * gap;
  const x0 = (w - total) / 2;
  return x0 + i * (cw + gap);
}
function handY(seat, h, d) {
  const [, ch] = d || dims();
  if (seat === SOUTH) return h - ch - 8;
  if (seat === NORTH) return 24;
  return h / 2 - ch / 2;
}

// fixed per-seat anchor for the 4 played cards (stable, no sliding)
function trickPos(seat, cx, cy, cw, ch) {
  const rad = 52;
  if (seat === NORTH) return [cx - cw / 2, cy - rad - ch / 2];
  if (seat === SOUTH) return [cx - cw / 2, cy + rad - ch / 2];
  if (seat === WEST)  return [cx - rad - cw / 2, cy - ch / 2];
  return [cx + rad - cw / 2, cy - ch / 2]; // EAST
}

function render() {
  const cv = App.board;
  if (!cv) return;
  const w = cv.clientWidth, h = cv.clientHeight;
  if (!w || !h || w < 100 || h < 100) return;
  // draw at device resolution for crispness, in stage CSS-pixel coords
  const dpr = window.devicePixelRatio || 1;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
  }
  const ctx = App.ctx;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  // felt
  ctx.fillStyle = FELT; ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = FELT_EDGE; ctx.lineWidth = 4; ctx.strokeRect(2, 2, w - 4, h - 4);

  const [cw, ch] = dims();
  const [pcw, pch,] = playDims();
  const hands = App.game.hands;

  // seat name labels
  const names = {
    [NORTH]: t("seatDummy"), [SOUTH]: t("seatDealer"),
    [WEST]: t("west") + t("seatDef"), [EAST]: t("east") + t("seatDef")
  };
  const pos = {
    [NORTH]: [w / 2, 6, "center"], [SOUTH]: [w / 2, h - 6, "center"],
    [WEST]: [6, h / 2, "left"], [EAST]: [w - 6, h / 2, "right"]
  };
  ctx.font = "bold 10px 'Segoe UI', Arial, sans-serif";
  for (const seat of [NORTH, SOUTH, WEST, EAST]) {
    const [px, py, anchor] = pos[seat];
    ctx.fillStyle = (seat === SOUTH || seat === NORTH) ? "#fff2a6" : "#dfe8df";
    ctx.textBaseline = "middle";
    ctx.textAlign = anchor;
    ctx.fillText(names[seat], px, py);
  }

  // N/S hands (big).  MATCHES THE DESKTOP (bm2000/gui.py CardWidget + _render):
  // only the on-lead human hand's *legal* cards are highlighted gold; every
  // other card is drawn WHITE (face-up, normal) -- the inactive hand is NOT
  // grayed.  The bridge rule ("打牌限定"): you may play only a legal card of the
  // hand that is on lead; the rest simply aren't highlighted and aren't
  // clickable (enforced in onBoardClick).
  const toPlay = App.game.toPlay;
  const humanTurn = toPlay !== null && (toPlay === SOUTH || toPlay === NORTH) &&
    App.collectingWinner === null;
  const valid = humanTurn ? App.game.legal() : [];   // [] when it's the defense's turn
  for (const seat of [NORTH, SOUTH]) {
    const hand = hands[seat].slice().sort((a, b) => suitSeq(a.s) - suitSeq(b.s) || -a.r + b.r);
    const y = handY(seat, h, playDims());
    const x0 = handX(seat, 0, hand.length, w, playDims());
    hand.forEach((card, i) => {
      const x = x0 + i * (pcw + 4);
      // legal only if this hand is on lead AND the card is in the legal set
      const hl = (humanTurn && seat === toPlay) && valid.some((c) => sameCard(c, card));
      drawCard(ctx, x, y, pcw, pch, card, true, /*dim*/ false, /*highlight*/ hl);
    });
  }

  // W/E face-down fans (base size)
  for (const seat of [WEST, EAST]) {
    const hand = hands[seat];
    const n = hand.length;
    const y = handY(seat, h);
    const x = seat === WEST ? 40 : w - 40 - cw;
    for (let i = 0; i < n; i++) {
      const yy = y - ((n - 1) * (ch * 0.5)) / 2 + i * (ch * 0.5);
      drawBack(ctx, x, yy, cw, ch);
    }
  }

  // center trick
  let showTrick = App.game.trick.slice();
  let showWinner = showTrick.length ? trickWinner(showTrick, App.game.trump) : null;
  if (App.collectingWinner !== null && App.game.tricks.length) {
    showTrick = App.game.tricks[App.game.tricks.length - 1].slice();
    showWinner = App.collectingWinner;
  }
  if (showTrick.length) {
    const collecting = App.collectingWinner !== null;
    for (const p of showTrick) {
      const [tx, ty] = trickPos(p.seat, w / 2, h / 2, pcw, pch);
      const isWin = showWinner !== null && p.seat === showWinner;
      if (isWin) { // glow ring behind the winner
        ctx.fillStyle = "rgba(255,210,74,.35)";
        ctx.fillRect(tx - 3, ty - 3, pcw + 6, pch + 6);
      }
      drawCard(ctx, tx, ty, pcw, pch, p.card, true, false, isWin);
      if (collecting && isWin) {
        ctx.fillStyle = "#ffd24a";
        ctx.font = "bold 9px Arial, sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "bottom";
        ctx.fillText(t("win"), tx + pcw / 2, ty - 2);
      }
    }
  }

  // NS/EW strip
  const won = App.game.wonNS;
  const ew = App.game.tricks.length - won;
  const cur = App.game.tricks.length + (App.game.trick.length ? 1 : 0);
  $("playStrip").innerHTML = stripHtml(won, ew, cur);

  // narration
  renderNarr();
}

// Build the top info strip as three readable rows (bigger than the old 22px/11px
// bar the user complained about).  Line 1 = live score, line 2 = the full
// auction/bidding, line 3 = contract + vulnerability + HCP of the two human hands.
function stripHtml(won, ew, cur) {
  const d = App.curDealData;
  if (!d) return "";
  const contract = d.contract ? (d.contract.text + "  (" + t("by") + " " +
    seatLabel(d.contract.seat) + ")") : t("passout");
  const vuln = d.contract ? ('<span class="vuln">&nbsp;&nbsp;' + t("vuln") + ": " + vulnText(d.vuln) + "</span>") : "";
  const hcp = '<span class="vuln">&nbsp;&nbsp;' + t("hcp") + '&nbsp; S:' + d.hcp[0] + "  N:" + d.hcp[2] + "</span>";
  const auction = d.auction.map((x) => x.bid).join("   ");
  return '<div class="row row-score">' +
            '<span class="ns">NS&nbsp;' + won + "</span>" +
            '&nbsp;&nbsp;&nbsp;<span class="ew">EW&nbsp;' + ew + "</span>" +
            "&nbsp;&nbsp;&nbsp;" + t("trick") + "&nbsp; " + cur + "/13" +
            "</div>" +
          '<div class="row row-auction" title="' + auction + '">' + auction + "</div>" +
          '<div class="row row-contract"><b>' + contract + "</b>" + vuln + hcp + "</div>";
}

function setNarr(t) {
  $("narr").textContent = t || "";
}

function renderNarr() {
  if (App.collectingWinner !== null) return;       // keep the "collecting..." line
  if (App.movieMode) {
    const total = App.narrPages.length;
    const cur = Math.min(App.moviePage, Math.max(0, total - 1));
    // the expert captions come from the original deck data in English; when the
    // UI is in another language, say so so the user isn't confused.
    const note = (App.lang !== "en" && App.narrPages.length) ? "\n" + t("englishNote") : "";
    $("narr").textContent = total
      ? t("movieCap", cur, total) + "\n" + App.narrPages[cur] + note
      : t("movieEnd");
    return;
  }
  const page = App.narrPages[Math.min(App.game.tricksPlayed, App.narrPages.length - 1)];
  $("narr").textContent = page || "";
}

// ---------------------------------------------------------------------------
//  end-of-deal flashy dialog
// ---------------------------------------------------------------------------
function showEndDialog() {
  const [won, level] = App.game.score;
  const d = App.curDealData;
  const made = d && d.contract ? won >= level : true;
  const word = d && d.contract ? (made ? t("dealWord") : t("failWord")) : t("passWord");
  const wEl = $("endWord");
  wEl.textContent = word;
  wEl.className = "end-word beat " + (made || !d || !d.contract ? "made" : "down");
  const nsL = t("south"), ewL = t("east");
  // score line: NS took `won`, the contract required `level` tricks.  (We stop
  // as soon as the result is decided, so `won` is the declarer's final total.)
  $("endScore").textContent =
    nsL + "  " + won + "      " + ewL + "  " + (13 - won) + "      (" + t("endScoreNeeds") + " " + level + ")";
  const expert = ["Schenker", "Auken", "Horenstein", "Palliser", "Terkelsen"][App.curDeal % 5];
  // Original semantics: the contract is simply made / defeated; a named expert
  // rating is awarded only when the contract is made.
  let sub;
  if (!d || !d.contract) sub = t("passOutSub");
  else if (made) sub = t("madeSub", d.contract.text, won, level) +
    "   " + t("expert") + ": " + expert;
  else sub = t("downSub", d.contract.text, won, level);
  $("endSub").textContent = sub;

  // record the result for the TOC marks
  const key = App.curLevel + ":" + App.curDeal;
  App.results[key] = made ? "made" : "down";

  $("endModal").classList.remove("hidden");
}

function hideEndDialog() { $("endModal").classList.add("hidden"); }

// ---------------------------------------------------------------------------
//  board click: play a card
// ---------------------------------------------------------------------------
function onBoardClick(ev) {
  if (App.movieMode) return;
  const seat = App.game.toPlay;
  if (seat !== SOUTH && seat !== NORTH) return;
  if (App.collectingWinner !== null || App.game.done) return;
  const cv = App.board;
  const rect = cv.getBoundingClientRect();
  // the canvas CSS size is scaled by the stage transform; convert to stage px
  const scale = rect.width / cv.clientWidth || 1;
  const x = (ev.clientX - rect.left) / scale;
  const y = (ev.clientY - rect.top) / scale;
  const w = cv.clientWidth, h = cv.clientHeight;
  const [pcw, pch] = playDims();
  // display order matches render(): suit groups (s,h,d,c) then rank high->low
  const hand = App.game.hands[seat].slice().sort((a, b) =>
    suitSeq(a.s) - suitSeq(b.s) || -a.r + b.r);
  const yH = handY(seat, h, playDims());
  const x0 = handX(seat, 0, hand.length, w, playDims());
  for (let i = 0; i < hand.length; i++) {
    const cx = x0 + i * (pcw + 4);
    if (x >= cx && x <= cx + pcw && y >= yH && y <= yH + pch) {
      const card = hand[i];
      const idx = App.game.hands[seat].findIndex((c) => sameCard(c, card));
      playCard(idx, seat);
      return;
    }
  }
}

// display order for a single card's suit: spades, hearts, diamonds, clubs
function suitSeq(s) { return [3, 2, 1, 0].indexOf(s); }

// ---------------------------------------------------------------------------
//  startup
// ---------------------------------------------------------------------------
async function main() {
  App.board = $("board");
  if (!App.board) return;      // e.g. selftest.html has no canvas; skip play UI
  App.ctx = App.board.getContext("2d");
  window.addEventListener("resize", fitStage);
  fitStage();
  App.board.addEventListener("click", onBoardClick);

  applyLocaleUI();

  // dialog buttons
  $("btnRestart").onclick = () => { hideEndDialog(); resetGame(); };
  $("btnAnswer").onclick = () => {
    hideEndDialog();
    App.movieMode = true;
    App.moviePage = 0;
    App.collectingWinner = null;
    render();
    movieBtn();
    movieAutoNext();
  };
  $("btnNext").onclick = () => {
    hideEndDialog();
    const lv = App.data.levels.find((l) => l.level === App.curLevel);
    const next = (App.curDeal + 1) % lv.deals.length;
    playDeal(App.curLevel, next);
  };

  let data;
  try {
    const r = await fetch("/api/deals", { cache: "no-cache" });
    data = await r.json();
  } catch (e) {
    $("status").textContent = t("failedLoad") + ": " + e;
    return;
  }
  App.data = data;
  buildTOC();
  applyLocaleUI();
  selectLevel(1);

  // optional URL hooks for screenshots/automation:
  //   ?level=N&deal=K  (0-based) opens that deal;  &autoplay=1 plays a few
  const q = new URLSearchParams(location.search);
  const lvl = parseInt(q.get("level"), 10);
  const dl = parseInt(q.get("deal"), 10);
  if (!isNaN(lvl) && !isNaN(dl)) {
    const lv = App.data.levels.find((l) => l.level === lvl);
    if (lv && lv.deals[dl]) playDeal(lvl, dl);
  }
  if (q.get("autoplay") === "1" && App.game) autoplayForShot();
}

// translate every static element tagged [data-i18n] (plus the <title>) for
// the current locale and wire up the EN / 中文 toggle.
function applyLocaleUI() {
  const map = { restart: "restart", showAnswer: "showAnswer", nextDeal: "nextDeal", loading: "loading" };
  document.querySelectorAll("[data-i18n]").forEach((e) => {
    const k = e.getAttribute("data-i18n");
    if (map[k]) e.textContent = t(k);
  });
  if (document.title !== t("pageTitle")) { document.title = t("pageTitle"); document.documentElement.lang = App.lang; }
  const en = $("langEn"), zh = $("langZh");
  if (en) { en.classList.toggle("on", App.lang === "en"); en.onclick = () => setLocale("en"); }
  if (zh) { zh.classList.toggle("on", App.lang === "zh"); zh.onclick = () => setLocale("zh"); }
}

// play a handful of tricks (declarer = highest legal, defense = convention)
function autoplayForShot() {
  let count = 0;
  const tick = () => {
    if (App.game.done || App.collectingWinner !== null || count > 40) {
      setTimeout(tick, App.collectMs || 400);
      return;
    }
    const seat = App.game.toPlay;
    if (seat === null) return;
    if (seat === SOUTH || seat === NORTH) {
      const legal = App.game.legal();
      legal.sort((a, b) => b.r - a.r);     // play a high card for a lively shot
      const top = legal[0];
      const idx = top ? App.game.hands[seat].findIndex((c) => sameCard(c, top)) : -1;
      if (idx >= 0) playCard(idx, seat);
    } else {
      pushUndo();
      App.game.defenseStep();
      afterPlay();
    }
    count++;
    setTimeout(tick, 260);
  };
  tick();
}

document.addEventListener("DOMContentLoaded", main);
