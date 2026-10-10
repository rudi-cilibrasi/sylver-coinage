// The Sylver Coinage Story: a history in twelve chapters, as a deterministic
// canvas film. renderAt(ctx, t) draws the frame at t seconds on a 1920x1080
// stage, so the same code drives the player in story.html, the frame-by-frame
// MP4 render (render-story.mjs) and the node tests.
"use strict";

const W = 1920, H = 1080;
const C = {
  ground: "#141a24", groundDeep: "#0c1017", panel: "#1b2331", line: "#2b3546",
  silver: "#cfd5dd", silverHi: "#f3f5f8", silverLo: "#8a94a2",
  copper: "#c77d45", copperHi: "#e9a46c", copperLo: "#7a4a2a",
  verdigris: "#5fae9e", verdigrisLo: "#2f6158", oxide: "#cf5a43", oxideLo: "#6e2c22",
  text: "#e9edf2", muted: "#98a3b2", faint: "#5b6676", gilt: "#d9b26a",
};
const F = {
  display: '"Cinzel", "Trajan Pro", "Times New Roman", serif',
  body: '"Spectral", Georgia, "Times New Roman", serif',
  mono: '"IBM Plex Mono", "DejaVu Sans Mono", monospace',
};

// ---------- timing helpers ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, p) => a + (b - a) * p;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeInOut = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
const easeOut = (p) => 1 - Math.pow(1 - p, 3);
const easeBack = (p) => { const c = 1.6; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
// fade in over [a, a+d], hold, fade out over [b-d, b]
const window_ = (t, a, b, d = 0.6) => Math.min(seg(t, a, a + d), 1 - seg(t, b - d, b));

// ---------- drawing helpers ----------
function text(ctx, s, x, y, o = {}) {
  const { size = 40, font = F.body, weight = 400, style = "", color = C.text, align = "left",
          alpha = 1, spacing = 0, baseline = "alphabetic" } = o;
  if (alpha <= 0) return 0;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.font = `${style} ${weight} ${size}px ${font}`;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = baseline;
  if ("letterSpacing" in ctx) ctx.letterSpacing = `${spacing}px`;
  ctx.fillText(s, x, y);
  const w = ctx.measureText(s).width;
  ctx.restore();
  return w;
}

function wrap(ctx, s, maxWidth, font) {
  ctx.save();
  ctx.font = font;
  const words = s.split(" "), lines = [];
  let line = "";
  for (const word of words) {
    const test = line ? line + " " + word : word;
    if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = word; } else line = test;
  }
  if (line) lines.push(line);
  ctx.restore();
  return lines;
}

// The captions of the frame being drawn (alpha above one half), so the page can show them as text too.
let shownCaptions = null;
function caption(ctx, s, alpha) {
  if (shownCaptions && alpha > 0.5 && !shownCaptions.includes(s)) shownCaptions.push(s);
  if (alpha <= 0) return;
  const size = 40, font = `400 ${size}px ${F.body}`;
  const lines = wrap(ctx, s, 1480, font);
  const lh = size * 1.32, y0 = 905 - (lines.length - 1) * lh / 2;
  lines.forEach((ln, i) => text(ctx, ln, W / 2, y0 + i * lh, { size, align: "center", alpha, color: C.text }));
}

function eyebrow(ctx, s, alpha) {
  text(ctx, s, 96, 112, { size: 30, font: F.display, weight: 600, color: C.gilt, spacing: 4, alpha });
  ctx.save();
  ctx.globalAlpha = alpha * 0.8;
  ctx.fillStyle = C.gilt;
  ctx.fillRect(96, 130, 64, 3);
  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// A minted coin: metal disc, beaded rim, embossed numeral. squash in [0,1] fakes a spin.
function coin(ctx, x, y, r, label, o = {}) {
  const { metal = "silver", alpha = 1, squash = 1, legend = null, labelSize = null } = o;
  if (alpha <= 0) return;
  const pal = metal === "copper" ? [C.copperHi, C.copper, C.copperLo] : metal === "oxide"
    ? ["#e98a74", C.oxide, C.oxideLo] : metal === "verdigris" ? ["#9fd6ca", C.verdigris, C.verdigrisLo]
    : [C.silverHi, C.silver, C.silverLo];
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.translate(x, y);
  ctx.scale(Math.max(0.02, squash), 1);
  const g = ctx.createRadialGradient(-r * 0.35, -r * 0.4, r * 0.1, 0, 0, r * 1.05);
  g.addColorStop(0, pal[0]); g.addColorStop(0.55, pal[1]); g.addColorStop(1, pal[2]);
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = Math.max(1, r * 0.03);
  ctx.beginPath(); ctx.arc(0, 0, r * 0.86, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = "rgba(20,26,36,0.28)";
  const beads = Math.max(24, Math.round(r / 2.2));
  for (let i = 0; i < beads; i++) {
    const a = (i / beads) * Math.PI * 2;
    ctx.beginPath(); ctx.arc(Math.cos(a) * r * 0.93, Math.sin(a) * r * 0.93, Math.max(0.8, r * 0.022), 0, Math.PI * 2); ctx.fill();
  }
  if (legend) {
    ctx.font = `600 ${Math.round(r * 0.11)}px ${F.display}`;
    ctx.fillStyle = "rgba(20,26,36,0.62)";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    const chars = legend.split("");
    const span = Math.PI * 1.1, start = -Math.PI / 2 - span / 2;
    chars.forEach((ch, i) => {
      const a = start + (i + 0.5) * span / chars.length;
      ctx.save(); ctx.rotate(a + Math.PI / 2); ctx.fillText(ch, 0, -r * 0.74); ctx.restore();
    });
  }
  if (label !== null && label !== undefined) {
    const fs = labelSize || Math.round(r * (String(label).length > 2 ? 0.62 : 0.8));
    ctx.font = `600 ${fs}px ${F.mono}`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillStyle = "rgba(255,255,255,0.45)";
    ctx.fillText(String(label), -fs * 0.03, fs * 0.05 - fs * 0.04);
    ctx.fillStyle = "rgba(15,20,28,0.78)";
    ctx.fillText(String(label), 0, fs * 0.05);
  }
  ctx.restore();
}

// A number tile in the strip/grid. state: open | minted | named | lose | win | unknown | frontier
function tile(ctx, x, y, w, h, n, state, o = {}) {
  const { alpha = 1, glow = 0, sub = null, size = null } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  const st = {
    open: [C.panel, C.copper, C.copperHi], minted: ["#202836", C.line, C.faint], named: [C.silver, C.silverHi, C.groundDeep],
    lose: [C.oxideLo, C.oxide, "#ffd9cf"], win: [C.verdigrisLo, C.verdigris, "#dff5ef"],
    unknown: [C.panel, C.silverLo, C.silver], frontier: ["#2c2416", C.gilt, "#f6e2b5"],
  }[state];
  if (glow > 0) { ctx.shadowColor = state === "lose" ? C.oxide : state === "frontier" ? C.gilt : C.copper; ctx.shadowBlur = 28 * glow; }
  roundRect(ctx, x, y, w, h, Math.min(14, h * 0.18));
  ctx.fillStyle = st[0]; ctx.fill();
  ctx.shadowBlur = 0;
  ctx.lineWidth = state === "minted" ? 1.5 : 2.5;
  ctx.strokeStyle = st[1]; ctx.stroke();
  const fs = size || Math.round(h * 0.46);
  text(ctx, String(n), x + w / 2, y + h / 2 + (sub ? -h * 0.08 : 0), {
    size: fs, font: F.mono, weight: state === "minted" ? 400 : 600, color: st[2], align: "center", baseline: "middle",
    alpha: state === "minted" ? 0.55 : 1,
  });
  if (sub) text(ctx, sub, x + w / 2, y + h * 0.82, { size: Math.round(h * 0.17), font: F.body, color: st[2], align: "center", baseline: "middle", alpha: 0.9 });
  ctx.restore();
}

// ---------- semigroup arithmetic ----------
function paid(gens, limit) {
  const r = new Array(limit + 1).fill(false); r[0] = true;
  for (let n = 1; n <= limit; n++) r[n] = gens.some((g) => g <= n && r[n - g]);
  return r;
}

// ---------- background and history ribbon ----------
const RIBBON = [[1880, 0], [1980, 0.22], [2000, 0.42], [2010, 0.55], [2020, 0.72], [2026.8, 1]];
function ribbonX(year) {
  for (let i = 1; i < RIBBON.length; i++) {
    const [y0, p0] = RIBBON[i - 1], [y1, p1] = RIBBON[i];
    if (year <= y1) return 160 + (W - 320) * lerp(p0, p1, clamp((year - y0) / (y1 - y0)));
  }
  return W - 160;
}

function background(ctx) {
  ctx.fillStyle = C.ground;
  ctx.fillRect(0, 0, W, H);
  const g = ctx.createRadialGradient(W * 0.5, H * 0.45, H * 0.2, W * 0.5, H * 0.5, H * 1.05);
  g.addColorStop(0, "rgba(40,52,72,0.35)"); g.addColorStop(1, "rgba(5,8,12,0.55)");
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}

const MILESTONES = [
  [1884, "Sylvester"], [1982, "Winning Ways"], [1991, ""], [1996, ""], [2002, "Sicherman"], [2014, "$1,000"],
  [2020, ""], [2021, "Blok"], [2022, ""], [2024, ""], [2026, "2026"],
];
function ribbon(ctx, year, alpha) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha = alpha;
  const y = 1028;
  ctx.strokeStyle = C.line; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(160, y); ctx.lineTo(W - 160, y); ctx.stroke();
  for (const [yr, label] of MILESTONES) {
    const x = ribbonX(yr), past = year >= yr - 0.01;
    ctx.fillStyle = past ? C.gilt : C.faint;
    ctx.beginPath(); ctx.arc(x, y, past ? 5 : 3.5, 0, Math.PI * 2); ctx.fill();
    if (label) text(ctx, label, x, y - 16, { size: 18, font: F.body, color: past ? C.muted : C.faint, align: "center" });
  }
  if (year) {
    const x = ribbonX(year);
    ctx.fillStyle = C.gilt;
    ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 8, y + 2); ctx.lineTo(x - 8, y + 2); ctx.closePath(); ctx.fill();
    text(ctx, String(Math.floor(year)), x, y + 34, { size: 20, font: F.mono, color: C.gilt, align: "center" });
  }
  ctx.restore();
}

// ---------- chapters ----------
// Each chapter: [start, end, year-on-ribbon or null, eyebrow, draw(ctx, t, d)] with t local.
const CH = [];
const chapter = (dur, year, brow, draw, name) => CH.push({ dur, year, brow, draw, name });

// 0. Title
chapter(9, null, null, (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  const spin = easeOut(seg(t, 0.2, 2.4));
  coin(ctx, 600, 470, 250, "16", { alpha: a, squash: Math.abs(Math.cos((1 - spin) * Math.PI * 3)), legend: "SYLVER · COINAGE" });
  text(ctx, "SYLVER", 960, 400, { size: 118, font: F.display, weight: 700, color: C.silverHi, spacing: 10, alpha: a * seg(t, 0.8, 2.0) });
  text(ctx, "COINAGE", 960, 528, { size: 118, font: F.display, weight: 700, color: C.silver, spacing: 10, alpha: a * seg(t, 1.1, 2.3) });
  const sub = a * seg(t, 2.4, 3.6);
  text(ctx, "A game about coins, a formula from 1884,", 964, 616, { size: 40, style: "italic", color: C.muted, alpha: sub });
  text(ctx, "and the smallest opening nobody has solved.", 964, 668, { size: 40, style: "italic", color: C.muted, alpha: sub });
  text(ctx, "A HISTORY IN TWELVE CHAPTERS", 964, 760, { size: 24, font: F.display, color: C.gilt, spacing: 5, alpha: a * seg(t, 3.6, 4.6) });
}, "Title");

CH[CH.length - 1].text = ["Sylver Coinage: a game about coins, a formula from 1884, and the smallest opening nobody has solved."];
// 1. The game: a full example on tiles 1..36
const GAME = [
  [6.5, "A", 5], [14.0, "B", 7], [28.0, "A", 4], [31.5, "B", 6], [34.5, "A", 3], [37.5, "B", 2], [41.0, "A", 1],
];
chapter(48, null, "THE GAME", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  // tiles in a 9x4 grid
  const cols = 9, tw = 118, th = 86, gx = 20, gy = 18, x0 = 640, y0 = 220;
  const named = GAME.filter(([at]) => t >= at).map(([, , n]) => n);
  const last = GAME.filter(([at]) => t >= at).slice(-1)[0];
  const sinceLast = last ? t - last[0] : 99;
  const pay = paid(named.filter((n) => n !== 1), 36);
  for (let n = 1; n <= 36; n++) {
    const i = n - 1, x = x0 + (i % cols) * (tw + gx), y = y0 + Math.floor(i / cols) * (th + gy);
    const appear = seg(t, 0.3 + i * 0.03, 0.9 + i * 0.03);
    let state = "open", glow = 0;
    if (named.includes(n)) state = n === 1 ? "lose" : "named";
    else if (pay[n]) state = "minted";
    // stamp flash for numbers removed by the latest move
    if (last && !named.includes(n) && pay[n]) {
      const prev = paid(named.slice(0, -1).filter((m) => m !== 1), 36);
      if (!prev[n]) { const p = seg(sinceLast, 0.1 + (n % 9) * 0.04, 0.7 + (n % 9) * 0.04); glow = (1 - p) * 0.9; if (p < 1) state = p < 0.5 ? "open" : "minted"; }
    }
    if (state === "open" && t > 21.5 && t < 28) glow = 0.5 + 0.5 * Math.sin((t - 21.5) * 4);
    tile(ctx, x, y, tw, th, n, state, { alpha: a * appear, glow });
  }
  // players and the coins they named
  const py = [300, 560];
  ["A", "B"].forEach((p, k) => {
    text(ctx, "PLAYER " + p, 120, py[k], { size: 30, font: F.display, weight: 600, color: C.silver, spacing: 3, alpha: a });
    GAME.filter(([at, who]) => who === p && t >= at).forEach(([at, , n], j) => {
      const s = easeBack(seg(t, at, at + 0.5));
      coin(ctx, 160 + j * 112, py[k] + 90, 48 * s, n, { alpha: a, metal: n === 1 ? "oxide" : "silver" });
    });
  });
  // captions
  const caps = [
    [0.5, 6.5, "Two players take turns naming a positive whole number."],
    [6.5, 14, "Naming 5 removes every number you could pay with 5s: 10, 15, 20 and so on."],
    [14, 21.5, "Naming 7 removes every sum of 5s and 7s. Paid amounts can never be named again."],
    [21.5, 28, "With 5 and 7 on the table, only twelve amounts are still unpaid."],
    [28, 41, "Each move shrinks what is left: 4 leaves 1, 2, 3 and 6; then 6, 3 and 2 are named."],
    [41, 48, "Player A has nothing left but 1. Whoever is forced to name 1 loses."],
  ];
  for (const [s, e, c] of caps) caption(ctx, c, a * window_(t, s, e, 0.5));
}, "The game");

// 2. Sylvester, 1884
chapter(24, 1884, "1884 · JAMES JOSEPH SYLVESTER", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  coin(ctx, 300, 420, 120, 5, { alpha: a * seg(t, 0.4, 1.2), squash: 1 });
  coin(ctx, 300 + 270, 420, 120, 7, { alpha: a * seg(t, 0.8, 1.6) });
  const pay = paid([5, 7], 30);
  const x0 = 840, tw = 76, th = 70, gap = 8;
  for (let n = 1; n <= 30; n++) {
    const i = n - 1, x = x0 + (i % 12) * (tw + gap), y = 300 + Math.floor(i / 12) * (th + gap);
    const lit = seg(t, 2 + n * 0.06, 2.4 + n * 0.06);
    const big = n === 23 && t > 6;
    tile(ctx, x, y, tw, th, n, pay[n] ? "minted" : big ? "frontier" : "open",
         { alpha: a * lit, glow: big ? 0.6 + 0.4 * Math.sin(t * 3) : 0, size: 30 });
  }
  const f = a * seg(t, 6.5, 7.5);
  text(ctx, "largest unpaid amount", 300 + 135, 640, { size: 30, color: C.muted, align: "center", alpha: f });
  text(ctx, "5 × 7 − 5 − 7 = 23", 300 + 135, 712, { size: 54, font: F.mono, weight: 600, color: C.gilt, align: "center", alpha: f });
  const g = a * seg(t, 10, 11);
  text(ctx, "a · b − a − b", 1340, 640, { size: 54, font: F.mono, weight: 600, color: C.silverHi, align: "center", alpha: g });
  text(ctx, "for any two coins with no common factor", 1340, 700, { size: 30, color: C.muted, align: "center", alpha: g });
  caption(ctx, "With coins of 5 and 7 you can pay every amount from 24 up, but twelve smaller amounts are impossible.", a * window_(t, 1, 10, 0.5));
  caption(ctx, "Sylvester proved the largest impossible amount is a·b − a − b. The game is named in his honour.", a * window_(t, 10, d, 0.5));
}, "Sylvester");

// 3. Winning Ways, 1982
chapter(30, 1982, "1982 · WINNING WAYS", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  // the book
  const ba = a * seg(t, 0.3, 1.3);
  ctx.save();
  ctx.globalAlpha = ba;
  roundRect(ctx, 150, 220, 380, 520, 10);
  const bg = ctx.createLinearGradient(150, 220, 530, 740);
  bg.addColorStop(0, "#1f4a3f"); bg.addColorStop(1, "#11291f");
  ctx.fillStyle = bg; ctx.fill();
  ctx.strokeStyle = C.gilt; ctx.lineWidth = 3;
  roundRect(ctx, 170, 240, 340, 480, 6); ctx.stroke();
  ctx.restore();
  text(ctx, "WINNING", 340, 330, { size: 46, font: F.display, weight: 700, color: C.gilt, align: "center", spacing: 4, alpha: ba });
  text(ctx, "WAYS", 340, 386, { size: 46, font: F.display, weight: 700, color: C.gilt, align: "center", spacing: 4, alpha: ba });
  text(ctx, "for your Mathematical Plays", 340, 432, { size: 24, style: "italic", color: "#e7d6ab", align: "center", alpha: ba });
  text(ctx, "Berlekamp · Conway · Guy", 340, 560, { size: 24, color: "#e7d6ab", align: "center", alpha: ba });
  text(ctx, "Chapter 18", 340, 640, { size: 22, font: F.display, color: C.gilt, align: "center", spacing: 2, alpha: ba });
  text(ctx, "The Emperor and His Money", 340, 676, { size: 24, style: "italic", color: "#e7d6ab", align: "center", alpha: ba });
  // three results
  const cards = [
    [5, "HUTCHINGS' THEOREM", "Open with a prime 5, 7, 11, 13 … and you can win. The proof steals a strategy, so it names no winning move."],
    [11, "THE QUIET END THEOREM", "In many positions it rules out infinitely many moves at once, leaving only finitely many to check."],
    [17, "THE PERIODICITY THEOREM", "When the named numbers have greatest common divisor 2, the winning moves after each odd move eventually repeat in a fixed pattern."],
  ];
  cards.forEach(([at, title, body], k) => {
    const p = easeOut(seg(t, at, at + 0.8)), y = 230 + k * 172;
    const ca = a * p;
    if (ca <= 0) return;
    ctx.save();
    ctx.globalAlpha = ca;
    roundRect(ctx, 640 + (1 - p) * 60, y, 1130, 148, 12);
    ctx.fillStyle = C.panel; ctx.fill();
    ctx.strokeStyle = C.line; ctx.lineWidth = 2; ctx.stroke();
    ctx.restore();
    text(ctx, title, 676 + (1 - p) * 60, y + 50, { size: 28, font: F.display, weight: 600, color: C.gilt, spacing: 2, alpha: ca });
    const lines = wrap(ctx, body, 1060, `400 30px ${F.body}`);
    lines.forEach((ln, i) => text(ctx, ln, 676 + (1 - p) * 60, y + 92 + i * 38, { size: 30, color: C.text, alpha: ca }));
  });
  caption(ctx, "John Horton Conway invented Sylver Coinage. Winning Ways gave it a chapter, and three theorems.", a * window_(t, 0.5, 23, 0.5));
  caption(ctx, "Every game must end, yet even the first move is hard to judge.", a * window_(t, 23, d, 0.5));
}, "Winning Ways");


// 4. Enders, quiet ends, short and long
chapter(32, 1982, "IDEAS · QUIET ENDS, SHORT AND LONG", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  // <4,7>: t = 17; pair k with 17 - k
  const T = 17, pay = paid([4, 7], T), tw = 82, th = 72, gap = 10, x0 = (W - 9 * tw - 8 * gap) / 2;
  const pa = a * seg(t, 0.5, 1.5);
  text(ctx, "Coins 4 and 7.  Largest unpaid amount: 17", W / 2, 220, { size: 34, color: C.muted, align: "center", alpha: pa });
  for (let k = 0; k <= 8; k++) {
    const top = k, bot = T - k, x = x0 + k * (tw + gap);
    const p = seg(t, 1.5 + k * 0.25, 2 + k * 0.25);
    tile(ctx, x, 270, tw, th, top, pay[top] ? "named" : "open", { alpha: pa * p, size: 32 });
    tile(ctx, x, 430, tw, th, bot, pay[bot] ? "named" : "open", { alpha: pa * p, size: 32 });
    const lp = a * seg(t, 4 + k * 0.2, 4.6 + k * 0.2);
    if (lp > 0) {
      ctx.save(); ctx.globalAlpha = lp; ctx.strokeStyle = C.gilt; ctx.lineWidth = 2; ctx.setLineDash([6, 6]);
      ctx.beginPath(); ctx.moveTo(x + tw / 2, 342); ctx.lineTo(x + tw / 2, 430); ctx.stroke(); ctx.restore();
    }
  }
  text(ctx, "k", x0 - 40, 316, { size: 30, font: F.mono, color: C.muted, align: "center", alpha: pa });
  text(ctx, "17−k", x0 - 52, 476, { size: 26, font: F.mono, color: C.muted, align: "center", alpha: pa });
  // doubled: {8,14}, then long {8,30,34}
  const s = a * seg(t, 13, 14);
  coin(ctx, 620, 650, 56, 8, { alpha: s });
  coin(ctx, 740, 650, 56, 14, { alpha: s });
  text(ctx, "short: finitely many moves to check", 820, 662, { size: 32, color: C.verdigris, alpha: s });
  const l = a * seg(t, 23, 24);
  coin(ctx, 560, 770, 46, 8, { alpha: l, metal: "copper" });
  coin(ctx, 660, 770, 46, 30, { alpha: l, metal: "copper" });
  coin(ctx, 760, 770, 46, 34, { alpha: l, metal: "copper" });
  text(ctx, "long: the only winning move is 49,337", 830, 782, { size: 32, color: C.copperHi, alpha: l });
  caption(ctx, "With 4 and 7 the unpaid amounts pair up: of k and 17 − k, exactly one can be paid. Such a position is a quiet ender.", a * window_(t, 1, 13, 0.5));
  caption(ctx, "Double a quiet ender, as in {8, 14}, and the Quiet End Theorem leaves only finitely many odd moves to check.", a * window_(t, 13, 23, 0.5));
  caption(ctx, "Positions without that structure are long. Some have astonishing answers, found only by computer.", a * window_(t, 23, d, 0.5));
}, "Quiet ends");

// 5. George Sicherman
chapter(28, 2002, "1991–2002 · GEORGE SICHERMAN", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  const items = [
    [0.6, "1991", "A report of many new computations, and a proof of the Single Win Theorem"],
    [2.6, "1996", "A second report, including the solution of {8, 30, 34}"],
    [4.6, "2002", "Theory and Practice of Sylver Coinage, in the journal Integers"],
    [6.6, "TODAY", "Tables of losing positions and community news at sicherman.net"],
  ];
  items.forEach(([at, yr, body], k) => {
    const p = easeOut(seg(t, at, at + 0.8)), y = 230 + k * 120, ia = a * p;
    text(ctx, yr, 160, y + 44, { size: 40, font: F.mono, weight: 600, color: C.gilt, alpha: ia });
    const lines = wrap(ctx, body, 700, `400 32px ${F.body}`);
    lines.forEach((ln, i) => text(ctx, ln, 330 + (1 - p) * 40, y + 30 + i * 40, { size: 32, color: C.text, alpha: ia }));
  });
  // {6, 40, 74}: every odd move loses; what repeats is the analysis of the replies
  const pa = a * seg(t, 10, 11);
  text(ctx, "Odd moves x in {6, 40, 74}", 1120, 260, { size: 30, color: C.muted, alpha: pa });
  for (let i = 0; i < 32; i++) {
    const shown = seg(t, 10.5 + i * 0.05, 10.8 + i * 0.05);
    ctx.save(); ctx.globalAlpha = pa * shown; ctx.fillStyle = C.oxide; ctx.fillRect(1120 + i * 21.5, 300, 18, 40); ctx.restore();
  }
  text(ctx, "every one loses: no odd move wins", 1120, 382, { size: 26, color: C.silver, alpha: pa * seg(t, 12, 12.6) });
  // the analysis behind it: an irregular start, then one block repeated exactly (schematic)
  const ra = a * seg(t, 12.6, 13.4), pre = [3, 1, 4, 0, 2, 4, 1, 3], block = [2, 0, 3, 1, 4, 2, 0, 1];
  pre.concat(block, block, block).forEach((v, i) => {
    ctx.save(); ctx.globalAlpha = ra; ctx.fillStyle = C.gilt;
    ctx.beginPath(); ctx.arc(1129 + i * 21.5, 470 - v * 11, 5, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  });
  const bx0 = 1120 + 8 * 21.5, bx1 = bx0 + 8 * 21.5 - 3.5;
  ctx.save(); ctx.globalAlpha = ra; ctx.strokeStyle = C.gilt; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(bx0, 482); ctx.lineTo(bx0, 492); ctx.lineTo(bx1, 492); ctx.lineTo(bx1, 482); ctx.stroke(); ctx.restore();
  text(ctx, "the analysis of the replies repeats (schematic)", 1120, 526, { size: 22, style: "italic", color: C.faint, alpha: ra });
  const q = a * seg(t, 14, 15);
  text(ctx, "period 403,200", 1120, 610, { size: 46, font: F.mono, weight: 600, color: C.gilt, alpha: q });
  text(ctx, "from x = 381,091", 1120, 662, { size: 32, font: F.mono, color: C.silver, alpha: q });
  caption(ctx, "George Sicherman spent decades computing positions, proving new theorems and keeping the community's tables.", a * window_(t, 0.5, 14, 0.5));
  caption(ctx, "His 2002 paper puts the Periodicity Theorem to work: no odd move wins in {6, 40, 74}, settled by a pattern that repeats every 403,200 from 381,091.", a * window_(t, 14, d, 0.5));
}, "Sicherman");
// 6. The openings and Conway's prize, 2014
const OPEN = { 1: "lose", 2: "lose", 3: "lose", 4: "lose", 5: "win", 6: "lose", 7: "win", 8: "lose", 9: "lose", 10: "lose",
               11: "win", 12: "lose", 13: "win", 14: "lose", 15: "lose", 16: "frontier", 17: "win" };
chapter(26, 2014, "2014 · CONWAY'S $1,000 QUESTION", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  const tw = 92, th = 112, gap = 10, x0 = (W - 17 * tw - 16 * gap) / 2, y = 330;
  for (let n = 1; n <= 17; n++) {
    const p = seg(t, 0.6 + n * 0.22, 1.1 + n * 0.22);
    const st = OPEN[n];
    const sub = st === "win" ? "wins" : st === "lose" ? "loses" : "?";
    const glow = n === 16 && t > 5 ? 0.6 + 0.4 * Math.sin(t * 3) : 0;
    tile(ctx, x0 + (n - 1) * (tw + gap), y, tw, th, n, p < 1 ? "unknown" : st, { alpha: a * Math.max(0.15, p), sub: p >= 1 ? sub : null, glow, size: 44 });
  }
  const q = a * seg(t, 12, 13);
  coin(ctx, W / 2, 640, 80, "$", { alpha: q, metal: "silver", labelSize: 74 });
  text(ctx, "1,000", W / 2 + 110, 664, { size: 64, font: F.mono, weight: 600, color: C.gilt, alpha: q });
  caption(ctx, "Every opening up to 15 is settled: the primes 5, 7, 11 and 13 win, and all the others lose.", a * window_(t, 0.5, 12, 0.5));
  caption(ctx, "Then comes 16. In 2014 Conway put it first among his Five $1,000 Problems: after the opening 16, who wins?", a * window_(t, 12, d, 0.5));
}, "Opening 16");

// 7. Numerical semigroups, 2020-2024
chapter(18, 2020, "2020–2024 · NUMERICAL SEMIGROUPS", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  const cards = [
    [0.6, "2020", "Eaton, Herzinger, Pierce and Thompson", "Numerical Semigroups and the Game of Sylver Coinage", "American Mathematical Monthly"],
    [2.4, "2024", "Boyers, Burton, Rushall, Warner and Zurick", "On winning strategies in Sylver Coinage when 4 has been chosen", "Integers 24"],
  ];
  cards.forEach(([at, yr, who, title, where], k) => {
    const p = easeOut(seg(t, at, at + 0.8)), x = 180 + k * 800, ca = a * p;
    if (ca <= 0) return;
    ctx.save(); ctx.globalAlpha = ca;
    roundRect(ctx, x, 260 + (1 - p) * 30, 740, 380, 12);
    ctx.fillStyle = "#e8e3d6"; ctx.fill(); ctx.restore();
    text(ctx, yr, x + 40, 330 + (1 - p) * 30, { size: 36, font: F.mono, weight: 600, color: "#7a4a2a", alpha: ca });
    const tl = wrap(ctx, title, 660, `600 36px ${F.body}`);
    tl.forEach((ln, i) => text(ctx, ln, x + 40, 400 + i * 46 + (1 - p) * 30, { size: 36, weight: 600, color: "#1b2230", alpha: ca }));
    const wl = wrap(ctx, who, 660, `400 28px ${F.body}`);
    wl.forEach((ln, i) => text(ctx, ln, x + 40, 520 + i * 36 + (1 - p) * 30, { size: 28, color: "#3a4352", alpha: ca }));
    text(ctx, where, x + 40, 600 + (1 - p) * 30, { size: 26, style: "italic", color: "#5b6676", alpha: ca });
  });
  caption(ctx, "Algebraists noticed that the paid amounts form a numerical semigroup once the named numbers share no factor, and new papers proved old claims about games after 4.", a * window_(t, 0.5, d, 0.5));
}, "Semigroups");

// 8. Thomas Blok
chapter(28, 2022, "2021–2026 · THOMAS BLOK", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  const items = [
    [0.6, "2021", "Sylver Coinage positions with g = 2: every even position containing an even number from 2 to 10, analysed completely"],
    [2.8, "2022", "Even positions in 14: every even position containing 14, analysed completely"],
    [5.0, "2026", "The 6-16 Tables, and in September new losing positions after the opening 16"],
  ];
  items.forEach(([at, yr, body], k) => {
    const p = easeOut(seg(t, at, at + 0.8)), y = 220 + k * 130, ia = a * p;
    text(ctx, yr, 160, y + 44, { size: 40, font: F.mono, weight: 600, color: C.gilt, alpha: ia });
    const lines = wrap(ctx, body, 880, `400 32px ${F.body}`);
    lines.forEach((ln, i) => text(ctx, ln, 330 + (1 - p) * 40, y + 30 + i * 40, { size: 32, color: C.text, alpha: ia }));
  });
  // the pairing family {8,12}, {8,10,12,14}, {8,12,18,22}, {8,12,26,30}
  const fam = [[8, 12], [8, 10, 12, 14], [8, 12, 18, 22], [8, 12, 26, 30]];
  text(ctx, "known losing positions by 2002; Blok's pairing proofs", 1330 - 44, 222, { size: 24, style: "italic", color: C.muted, alpha: a * seg(t, 9, 10) });
  fam.forEach((set, k) => {
    const fa = a * seg(t, 9 + k * 1.2, 10 + k * 1.2), y = 300 + k * 118;
    set.forEach((n, j) => coin(ctx, 1330 + j * 104, y, 44, n, { alpha: fa }));
    text(ctx, "P", 1330 + 4 * 104 + 10, y + 14, { size: 38, font: F.display, weight: 700, color: C.verdigris, alpha: fa });
  });
  caption(ctx, "Thomas Blok analysed the even positions systematically, and gave simple pairing proofs of losing positions already known, such as {8, 12}.", a * window_(t, 0.5, 15, 0.5));
  caption(ctx, "In September 2026 he proved {16, 26, 54, 60, 62} and {16, 28, 36, 38, 58} are losing positions too.", a * window_(t, 15, d, 0.5));
}, "Blok");

// 9. 2026: the campaign checks the published claims, and the authors answer
const CONFIRMATIONS = [
  [1.0, "JULY", "Replies 2 to 24 answered, confirming {16, 20, 34} from Sicherman's list and {10, 16, 24} from Blok's report"],
  [5.5, "JULY 24", "A periodicity engine re-derives {8, 10, 22}, Sicherman's first long losing position, from the 1990s"],
  [12.5, "AUG 27", "Sicherman's news page: the work “confirms Thomas Blok's analysis of {16}”"],
  [20.5, "SEPT 3", "Blok proves {16, 26, 54, 60, 62} is a losing position"],
  [23.0, "SEPT 5", "The campaign confirms it independently"],
];
chapter(32, 2026.3, "2026 · CONFIRMATIONS", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  CONFIRMATIONS.forEach(([at, when, body], k) => {
    const p = easeOut(seg(t, at, at + 0.8)), y = 196 + k * 118, ia = a * p;
    text(ctx, when, 160, y + 40, { size: 30, font: F.mono, weight: 600, color: C.gilt, alpha: ia });
    const lines = wrap(ctx, body, 720, `400 30px ${F.body}`);
    lines.forEach((ln, i) => text(ctx, ln, 350 + (1 - p) * 40, y + 40 + i * 38, { size: 30, color: C.text, alpha: ia }));
  });
  // George Sicherman's letter
  const p = easeOut(seg(t, 10.5, 11.5)), la = a * p, dy = (1 - p) * 30;
  if (la > 0) {
    ctx.save(); ctx.globalAlpha = la;
    roundRect(ctx, 1170, 210 + dy, 600, 500, 12);
    ctx.fillStyle = "#e8e3d6"; ctx.fill(); ctx.restore();
    const q = wrap(ctx, "“I have long wished for independent confirmation of our results.”", 520, `italic 400 42px ${F.body}`);
    q.forEach((ln, i) => text(ctx, ln, 1210, 290 + i * 56 + dy, { size: 42, style: "italic", color: "#1b2230", alpha: la }));
    const q2 = wrap(ctx, "And on {8, 10, 22}: “relieved to learn that your results agree with mine.”", 520, `italic 400 30px ${F.body}`);
    q2.forEach((ln, i) => text(ctx, ln, 1210, 488 + i * 40 + dy, { size: 30, style: "italic", color: "#3a4352", alpha: la }));
    text(ctx, "George Sicherman", 1210, 630 + dy, { size: 30, weight: 600, color: "#3a4352", alpha: la });
    text(ctx, "in a letter, August 27, 2026", 1210, 670 + dy, { size: 26, style: "italic", color: "#5b6676", alpha: la });
  }
  caption(ctx, "In July 2026 an AI-assisted campaign began answering the replies to 16. Every finite computation was replayed by two independent programs.", a * window_(t, 0.5, 10.5, 0.5));
  caption(ctx, "On the way it re-checked published claims, like Sicherman's {8, 10, 22}, first computed on a network of SUN workstations in the 1990s.", a * window_(t, 10.5, 20.5, 0.5));
  caption(ctx, "In September Thomas Blok proved new losing positions after 16, and the campaign confirmed the first within two days.", a * window_(t, 20.5, d, 0.5));
}, "Confirmations");

// 10. The 2026 campaign: replies to the opening 16
const REPLIES = [2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 26, 28, 30, 34, 36, 38];
const ANSWERS = { 2: 3, 4: 6, 6: 7, 8: 14, 10: 9, 12: 14, 14: 8, 18: 5, 20: 34, 22: 12, 24: 10, 26: 88, 28: 58, 30: 56, 34: 20, 36: 23 };
const WHEN = { 26: 19, 28: 23, 30: 25.5, 34: 28, 36: 30 };
const RULED_OUT_38 = [4, 6, 8, 12, 14, 22, 24, 28, 40, 44, 56];   // by certified P-positions
// [seconds into the chapter, the dated note shown]; the tests check the dates against the README
const NOTES = [
  [10.5, "July: replies 2 to 24 answered, each answer certified"],
  [19, "Oct 6: 26 loses to 88, after a search found 701 in {16, 26, 82, 88}"],
  [23, "Oct 7–8: 28 loses to 58, and 30 to 56"],
  [28, "Oct 9: a ledger shows every reply up to 36 has an answer"],
];
chapter(50, 2026.6, "2026 · MACHINE-CHECKED CERTIFICATES", (ctx, t, d) => {
  const a = window_(t, 0, d, 0.8);
  text(ctx, "16", 170, 330, { size: 96, font: F.mono, weight: 700, color: C.silverHi, alpha: a });
  text(ctx, "opening", 170, 370, { size: 26, color: C.muted, alpha: a });
  text(ctx, "replies", 360, 236, { size: 26, color: C.muted, alpha: a });
  text(ctx, "answers", 360, 470, { size: 26, color: C.muted, alpha: a });
  const tw = 78, th = 76, gap = 9, x0 = 360;
  REPLIES.forEach((r, i) => {
    const x = x0 + i * (tw + gap);
    const at = r <= 24 ? 10.5 : r === 38 ? 33 : WHEN[r];
    const p = seg(t, 1 + i * 0.1, 1.5 + i * 0.1);
    const done = t >= at + 0.6 && r !== 38;
    tile(ctx, x, 256, tw, th, r, r === 38 && t > 33 ? "frontier" : done ? "win" : "unknown",
         { alpha: a * p, size: 30, glow: r === 38 && t > 33 ? 0.6 + 0.4 * Math.sin(t * 3) : 0 });
    if (r !== 38) {
      const s = easeBack(seg(t, at, at + 0.6));
      if (s > 0) coin(ctx, x + tw / 2, 400, 32 * s, ANSWERS[r], { alpha: a, labelSize: ANSWERS[r] > 9 ? 22 : 26 });
    }
  });
  // the reply 38: candidate answers ruled out
  const oa = a * seg(t, 35, 36);
  text(ctx, "answers to 38 ruled out so far", 360, 560, { size: 28, color: C.muted, alpha: oa });
  RULED_OUT_38.forEach((n, i) => {
    const s = seg(t, 36 + i * 0.3, 36.4 + i * 0.3);
    tile(ctx, 360 + i * 87, 584, 78, 66, n, "lose", { alpha: oa * s, size: 28 });
  });
  const fa = a * seg(t, 42, 43);
  text(ctx, "38 ?", 1500, 680, { size: 64, font: F.mono, weight: 700, color: C.gilt, alpha: fa });
  // ledger of dates
  const live = NOTES.filter(([at]) => t >= at).slice(-1)[0];
  if (live) text(ctx, live[1], 360, 520, { size: 30, style: "italic", color: C.silver, alpha: a * window_(t, live[0], live[0] + 6, 0.4) });
  caption(ctx, "A reply loses when the opener has an answer that leaves a losing position. Two solvers must agree on every count.", a * window_(t, 0.5, 10, 0.5));
  caption(ctx, "Replies 2 to 24 fell in July. The replies above 24 took months of computing and new engines.", a * window_(t, 10, 18.5, 0.5));
  caption(ctx, "The hardest step, 701 in {16, 26, 82, 88}, took 633,734,956 positions, counted identically by two engines.", a * window_(t, 18.5, 27, 0.5));
  caption(ctx, "By October 9 every reply up to 36 had an answer. The reply 38 is the frontier.", a * window_(t, 27, 35, 0.5));
  caption(ctx, "Eleven possible answers to 38 are ruled out so far, by certified losing positions. None works yet.", a * window_(t, 35, d, 0.5));
}, "2026");

// 11. Closing
chapter(16, 2026.8, null, (ctx, t, d) => {
  const a = window_(t, 0, d, 1.0);
  coin(ctx, W / 2, 400, 200, "16", { alpha: a, legend: "WHO · WINS ·" });
  text(ctx, "Who wins after 16? Still open.", W / 2, 700, { size: 56, font: F.display, weight: 600, color: C.silverHi, align: "center", spacing: 2, alpha: a * seg(t, 1, 2) });
  text(ctx, "Play the game, check a certificate, or find an answer to 38.", W / 2, 770, { size: 36, style: "italic", color: C.muted, align: "center", alpha: a * seg(t, 2.5, 3.5) });
  const s = a * seg(t, 5, 6);
  text(ctx, "Sources: Winning Ways (1982) · Sicherman, Integers 2 (2002) and sicherman.net · Blok's reports (2021–2026)", W / 2, 880, { size: 24, color: C.faint, align: "center", alpha: s });
  text(ctx, "OEIS A248380 · Eaton et al. (2020) · Boyers et al. (2024) · github.com/rudi-cilibrasi/sylver-coinage", W / 2, 916, { size: 24, color: C.faint, align: "center", alpha: s });
}, "Open");

CH[CH.length - 1].text = ["Who wins after 16? Still open. Play the game, check a certificate, or find an answer to 38."];
// ---------- the timeline ----------
let acc = 0;
for (const c of CH) { c.start = acc; acc += c.dur; c.end = acc; }
const DURATION = acc;

function yearAt(t) {
  let year = null;
  for (const c of CH) if (c.year && t >= c.start) year = c.year;
  return year;
}

// Draw the frame at t seconds; returns the captions it shows.
function renderAt(ctx, t) {
  t = clamp(t, 0, DURATION - 1e-6);
  shownCaptions = [];
  ctx.save();
  background(ctx);
  const c = CH.find((x) => t >= x.start && t < x.end) || CH[CH.length - 1];
  const lt = t - c.start;
  if (c.brow) eyebrow(ctx, c.brow, window_(lt, 0, c.dur, 0.8));
  c.draw(ctx, lt, c.dur);
  ribbon(ctx, yearAt(t), t > CH[0].end - 1 ? clamp((t - CH[0].end + 1) / 1.5) : 0);
  ctx.restore();
  const shown = shownCaptions;
  shownCaptions = null;
  return shown;
}

// The film as text: each chapter's heading and its captions in order, from drawing every
// quarter second on a context that ignores the drawing.
const IGNORE = new Proxy({}, {
  get: (o, k) => (k === "measureText" ? () => ({ width: 0 }) : typeof k === "string" && k.startsWith("create") ? () => ({ addColorStop() {} }) : () => {}),
  set: () => true,
  has: () => false,
});
function transcript() {
  return CH.map((c) => {
    const lines = [];
    for (let t = 0; t < c.dur; t += 0.25) for (const line of renderAt(IGNORE, c.start + t)) if (!lines.includes(line)) lines.push(line);
    return { name: c.name, heading: c.brow, start: c.start, lines: lines.length ? lines : c.text || [] };
  });
}

if (typeof module !== "undefined") module.exports = { renderAt, transcript, DURATION, CHAPTERS: CH, W, H, ANSWERS, NOTES, REPLIES, RULED_OUT_38 };
else Object.assign(window, { renderAt, transcript, DURATION, CHAPTERS: CH });
