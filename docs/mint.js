// The Sylver Mint: nine small games that retrace the history of Sylver
// Coinage. Every game runs the repository's exact evaluator (solver.js). The
// answer table and the reply-38 frontier are exported so the node tests can
// check them against the campaign audits.
"use strict";

const NODE_SOLVER = typeof module !== "undefined" ? require("./solver.js") : null;
const Engine = NODE_SOLVER ? NODE_SOLVER.SylverSolver : SylverSolver;
const frobenius = NODE_SOLVER ? NODE_SOLVER.frobeniusNumber : frobeniusNumber;
// Whether n is paid in `state`; 0 and every amount above the Frobenius number are.
const isPaid = (solver, state, n) => n === 0 || n > solver.frobenius || ((state >> BigInt(n)) & 1n) === 1n;

function paidUpTo(gens, limit) {
  const r = new Array(limit + 1).fill(false); r[0] = true;
  for (let n = 1; n <= limit; n++) r[n] = gens.some((g) => g <= n && r[n - g]);
  return r;
}
const setText = (gens) => "{" + gens.join(", ") + "}";
function minimal(gens) {          // the smallest set of coins that pays the same amounts
  const out = [];
  for (const g of [...new Set(gens)].sort((a, b) => a - b)) if (!out.length || !paidUpTo(out, g)[g]) out.push(g);
  return out;
}
const plural = (n, word) => `${n.toLocaleString("en-US")} ${word}${n === 1 ? "" : "s"}`;

// ---------------------------------------------------------------- small DOM helpers
function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, "");
    else if (v !== false && v !== null && v !== undefined) e.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined) e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return e;
}
const P = (html) => { const p = document.createElement("p"); p.innerHTML = html; return p; };
function story(...paras) { return el("div", { class: "story" }, ...paras.map(P)); }
// Rebuilding a board drops keyboard focus: note the focused tile's number first, then put focus
// back on that number, or the next enabled tile above it, or the nearest below it (1 only as a last resort).
const focusedTile = (board) => (board.contains(document.activeElement) && document.activeElement.dataset.n ? Number(document.activeElement.dataset.n) : null);
function refocus(board, n) {
  if (n === null) return;
  const live = [...board.querySelectorAll("button[data-n]")].filter((b) => !b.disabled);
  const next = live.find((b) => Number(b.dataset.n) >= n) || live.filter((b) => b.dataset.n !== "1").pop() || live[0];
  if (next) next.focus();
}
const eyebrow = (label) => el("p", { class: "eyebrow" }, `LESSON ${current + 1} · ${label}`);

let done = new Set();
try { done = new Set(JSON.parse(localStorage.getItem("mint-done") || "[]")); } catch (e) { done = new Set(); }
function markDone(id) {
  done.add(id);
  try { localStorage.setItem("mint-done", JSON.stringify([...done])); } catch (e) { /* storage unavailable */ }
  renderNav();
}

// ---------------------------------------------------------------- lesson 1: play
function lessonPlay(root) {
  const presets = [[5, 7], [4, 9], [5, 6], [4, 7], [7, 9]];
  let solver, state, history, over, thinking = false, game = 0, hints = false;
  let want = null;                         // the tile to refocus once the computer has replied
  const msg = el("p", { class: "msg", "aria-live": "polite" });
  const board = el("div", { class: "tiles" });
  const picks = el("div", { class: "row" });
  const hintBtn = el("button", { class: "ctrl", type: "button", "aria-pressed": "false",
    onclick: () => { hints = !hints; hintBtn.setAttribute("aria-pressed", String(hints)); draw(); } }, "Show winning moves");
  const undo = el("button", { class: "ctrl", type: "button", onclick: () => {
    if (history.length >= 2 && !over && !thinking) {
      history.pop(); history.pop(); state = recompute();
      msg.className = "msg"; msg.textContent = "Took back your last move and the computer's reply. Your move.";
      draw();
    }
  } }, "Undo");
  const named = () => history.map((h) => h.m);
  function recompute() { let s = solver.initialState; for (const h of history) s = solver.adjoin(s, h.m); return s; }
  function start(gens) {
    game++;                                  // a reply still pending from the last game is dropped
    solver = new Engine(gens); history = []; over = false; thinking = false;
    state = solver.initialState;
    msg.className = "msg";
    msg.textContent = "Your move. Pick an unpaid amount.";
    draw();
  }
  function unpaid() { return [1, ...solver.legalMoves(state)]; }
  function end(loser, early) {
    over = true;
    msg.className = "msg " + (loser === "you" ? "lose" : "win");
    msg.textContent = loser === "you" ? (early ? "You named 1, so you lose. Try again, or turn on the hints."
                                               : "Only 1 was left for you. You lose this one. Try again, or turn on the hints.")
                                      : "The computer had to name 1. You win!";
    if (loser !== "you") markDone("play");
    draw();
  }
  function move(m, who) {
    history.push({ m, who });
    if (m === 1) { end(who, unpaid().length > 1); return; }
    state = solver.adjoin(state, m);
    if (unpaid().length === 1) { end(who === "you" ? "computer" : "you"); return; }
    draw();
  }
  function yourMove(m) {
    if (over || thinking) return;
    move(m, "you");
    if (over) return;
    want = m; thinking = true; draw();
    const mine = game;
    setTimeout(() => { if (mine === game) computer(); }, 450);
  }
  function computer() {
    thinking = false;
    if (over) return;
    const w = solver.winningMove(state), legal = solver.legalMoves(state);
    const m = w || (legal.length ? legal[legal.length - 1] : 1);
    msg.className = "msg";
    msg.textContent = `The computer names ${m}.` + (w ? "" : " (It is losing, so it plays for time.)");
    move(m, "computer");
  }
  function draw() {
    const keep = focusedTile(board) ?? want;
    board.replaceChildren();
    const gens = solver.gens, top = solver.frobenius;
    const winSet = new Set(), showHints = hints && !over && !thinking;
    if (showHints) for (const m of solver.legalMoves(state)) if (solver.winningMove(solver.adjoin(state, m)) === 0) winSet.add(m);
    for (let n = 1; n <= top; n++) {
      const isNamed = gens.includes(n) || named().includes(n);
      const paid = isPaid(solver, state, n) && n !== 1;
      let cls = "tile", hint = null;
      if (isNamed) cls += " named"; else if (paid) cls += " paid";
      else if (n === 1) cls += " one";
      else if (showHints) { hint = winSet.has(n) ? "wins" : "loses"; cls += winSet.has(n) ? " good" : " bad"; }
      board.append(el("button", { class: cls, type: "button", "data-n": n, disabled: isNamed || paid || over || thinking,
        "aria-label": `${n}${isNamed ? ", named" : paid ? ", paid" : hint ? `, ${hint}` : ""}`, onclick: () => yourMove(n) },
        el("span", {}, n), hint ? el("span", { class: "tag" }, hint) : null));
    }
    if (!thinking && keep !== null) { refocus(board, keep); want = null; }
  }
  presets.forEach((g, i) => picks.append(el("button", { class: "chip", type: "button", "aria-pressed": String(i === 0),
    onclick: (e) => { picks.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      e.currentTarget.setAttribute("aria-pressed", "true"); start(g); } }, "start at " + setText(g))));
  root.append(
    eyebrow("JOHN H. CONWAY'S GAME"),
    el("h2", {}, "Mint and lose"),
    story("Two players take turns naming a positive whole number. A number is <b>paid</b> once it is a sum of numbers already named, and paid numbers can never be named again. Whoever is forced to name <b>1</b> loses.",
          "The two silver coins are already named. Copper tiles are the amounts still unpaid, and grey tiles are paid. You move first, and the computer plays perfectly."),
    el("div", { class: "game" }, picks, board, msg, el("div", { class: "row" }, hintBtn, undo)),
    el("p", { class: "note" }, "Every position like these, two coins with no common factor other than {2, 3}, is a win for the player to move, so a winning move always exists. Finding it is the hard part."),
  );
  start(presets[0]);
}

// ---------------------------------------------------------------- lesson 2: Sylvester
function lessonSylvester(root) {
  const pairs = [[3, 5], [3, 7], [4, 5], [4, 7], [5, 6], [5, 7], [5, 8], [6, 7], [7, 8]];
  let a, b, marked, checked;
  const board = el("div", { class: "tiles" }), msg = el("p", { class: "msg", "aria-live": "polite" }), formula = el("p", { class: "formula" });
  const sel = el("select", { id: "syl-pair", "aria-label": "Two coins", onchange: () => setup(...sel.value.split(",").map(Number)) },
    ...pairs.map(([x, y]) => el("option", { value: `${x},${y}` }, `coins ${x} and ${y}`)));
  sel.value = "5,7";
  function setup(x, y) { a = x; b = y; marked = new Set(); checked = false; formula.textContent = ""; msg.className = "msg";
    msg.textContent = `Mark every amount from 1 to ${a * b} that cannot be paid with ${a}s and ${b}s.`; draw(); }
  function draw() {
    board.replaceChildren();
    const pay = paidUpTo([a, b], a * b);
    for (let n = 1; n <= a * b; n++) {
      let cls = "tile sm";
      if (checked) cls += pay[n] ? (marked.has(n) ? " bad" : " paid") : (marked.has(n) ? " good" : " gold");
      else if (marked.has(n)) cls += " pick";
      board.append(el("button", { class: cls, type: "button", disabled: checked, "aria-pressed": String(marked.has(n)),
        onclick: (e) => {
          marked.has(n) ? marked.delete(n) : marked.add(n);
          e.currentTarget.classList.toggle("pick", marked.has(n));
          e.currentTarget.setAttribute("aria-pressed", String(marked.has(n)));
        } }, n));
    }
  }
  const check = el("button", { class: "ctrl primary", type: "button", onclick: () => {
    const pay = paidUpTo([a, b], a * b), truth = [];
    for (let n = 1; n <= a * b; n++) if (!pay[n]) truth.push(n);
    const right = truth.filter((n) => marked.has(n)).length, wrong = [...marked].filter((n) => pay[n]).length;
    checked = true; draw();
    msg.className = "msg " + (right === truth.length && !wrong ? "win" : "");
    msg.textContent = `You found ${right} of the ${truth.length} unpayable amounts` + (wrong ? `, and marked ${wrong} that can be paid.` : ".");
    formula.textContent = `largest: ${a}×${b} − ${a} − ${b} = ${a * b - a - b}     count: (${a}−1)(${b}−1)/2 = ${(a - 1) * (b - 1) / 2}`;
    if (right === truth.length && !wrong) markDone("sylvester");
  } }, "Check");
  root.append(
    eyebrow("J. J. SYLVESTER, 1884"),
    el("h2", {}, "The largest unpayable amount"),
    story("Sylvester asked which amounts can be paid with coins of two values. When the values share no common factor, every large amount can be paid, and only finitely many small ones cannot.",
          "He proved the largest unpayable amount is <b>a·b − a − b</b>. The game is named in his honour. Find the unpayable amounts yourself, then check."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("label", { for: "syl-pair" }, "Coins"), sel, check), board, msg, formula),
  );
  setup(5, 7);
}

// ---------------------------------------------------------------- lesson 3: enders
function lessonEnders(root) {
  const options = [[5, 6], [5, 7], [5, 8], [5, 9], [7, 8], [7, 9], [7, 10]];
  let gens, t, tried;
  const board = el("div", { class: "tiles" }), msg = el("p", { class: "msg", "aria-live": "polite" });
  const sel = el("select", { id: "end-pair", "aria-label": "Position", onchange: () => setup(sel.value.split(",").map(Number)) },
    ...options.map((g) => el("option", { value: g.join(",") }, "position " + setText(g))));
  const reveal = el("p", { class: "note" });
  function setup(g) {
    gens = g; t = g[0] * g[1] - g[0] - g[1]; tried = new Set(); reveal.textContent = "";
    msg.className = "msg";
    msg.innerHTML = `The largest unpaid amount is <b>t = ${t}</b>. Click any other unpaid amount to see what it does to ${t}.`;
    draw();
  }
  function draw() {
    board.replaceChildren();
    const pay = paidUpTo(gens, t);
    for (let n = 1; n <= t; n++) {
      if (pay[n]) continue;
      const cls = "tile" + (n === t ? " gold" : tried.has(n) ? " good" : "");
      board.append(el("button", { class: cls, type: "button", onclick: (e) => explain(n, e.currentTarget) }, n));
    }
  }
  function explain(u, tile) {
    const pay = paidUpTo(gens, t);
    if (u === t) { msg.className = "msg"; msg.innerHTML = `${t} is the one move that removes nothing else: it is the <i>end</i>.`; return; }
    tried.add(u); tile.classList.add("good");
    if (u === 1) { msg.className = "msg lose"; msg.textContent = "Naming 1 loses at once."; return; }
    msg.className = "msg";
    msg.innerHTML = `Naming ${u} pays ${t}: ${t} = ${u} + ${t - u}, and ${t - u} ${pay[t - u] ? "is already paid" : "is paid too"}.`;
    const left = [];
    for (let n = 2; n < t; n++) if (!pay[n] && !tried.has(n)) left.push(n);
    if (!left.length) finish();
  }
  function finish() {
    const s = new Engine(gens), w = s.winningMove(s.initialState);
    reveal.innerHTML = `Every move except ${t} also pays ${t}, so ${setText(gens)} is an <b>ender</b>. Suppose naming ${t} lost to some reply u. Then naming u first would reach the same position and win. Either way the player to move can win. Here the computer finds the winning move: <b>${w}</b>.`;
    markDone("enders");
  }
  root.append(
    eyebrow("HUTCHINGS' THEOREM, IN WINNING WAYS (1982)"),
    el("h2", {}, "Steal a strategy"),
    story("R. L. Hutchings' theorem rests on <b>enders</b>: positions where every legal move except the largest unpaid amount t also pays t. Every position made of two coins with no common factor is one.",
          "A strategy-stealing argument shows the player to move in an ender can win, unless only 1 is left, as in {2, 3}. After the opening 5, 7, 11, 13 or any larger prime, every reply leaves such a position, so a prime opening wins. The proof names no winning move."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("label", { for: "end-pair" }, "Try"), sel), board, msg, reveal),
  );
  setup(options[1]);
  sel.value = options[1].join(",");
}

// ---------------------------------------------------------------- lesson 4: quiet ends
function lessonQuiet(root) {
  const options = [[4, 7], [5, 6], [4, 5, 7], [6, 8, 11], [8, 10, 11, 12], [4, 6, 9]];
  let gens, t;
  const kinds = new Set();
  const pairsBox = el("div", { class: "pairs" }), verdict = el("p", { class: "msg", "aria-live": "polite" }), doubled = el("div", { class: "story" });
  const sel = el("select", { id: "quiet-pos", "aria-label": "Position", onchange: () => setup(sel.value.split(",").map(Number)) },
    ...options.map((g) => el("option", { value: g.join(",") }, setText(g))));
  function setup(g) {
    gens = g; t = frobenius(g);
    const pay = paidUpTo(g, t);
    pairsBox.replaceChildren();
    const top = el("div", { class: "tiles" }), bot = el("div", { class: "tiles" });
    let quiet = true;
    for (let k = 0; k <= Math.floor(t / 2); k++) {
      const one = pay[k] !== pay[t - k];
      if (!one) quiet = false;
      top.append(el("span", { class: "tile sm " + (pay[k] ? "paid" : one ? "" : "bad") }, k));
      bot.append(el("span", { class: "tile sm " + (pay[t - k] ? "paid" : one ? "" : "bad") }, t - k));
    }
    pairsBox.append(el("div", { class: "row" }, el("span", { class: "lab" }, "k"), top), el("div", { class: "row" }, el("span", { class: "lab" }, `${t}−k`), bot));
    verdict.className = "msg " + (quiet ? "win" : "lose");
    verdict.textContent = quiet ? `Quiet ender: in every pair exactly one amount is paid (t = ${t}).`
                                : `Not quiet: some pair has both amounts unpaid (marked), so this ender is "unquiet".`;
    if (quiet) {
      const gaps = [];
      for (let n = 1; n <= t; n++) if (!pay[n]) gaps.push(n);
      const odd = gaps.filter((n) => n > 1 && n % 2), even = gaps.map((n) => 2 * n);
      doubled.innerHTML = `<p>Double it: <b>${setText(g.map((x) => 2 * x))}</b>. Now every named number is even, so infinitely many odd moves are legal. The Quiet End Theorem shows every odd move except the odd unpaid amounts ${odd.length ? odd.join(", ") : "(none)"} leaves a quiet ender, which loses for the player who made it. So this doubled position is <b>short</b>: only ${odd.length} odd and ${even.length} even moves (${even.join(", ")}) need checking.</p>`;
    } else {
      doubled.innerHTML = `<p>Doubling an unquiet position gives a <b>long</b> one. The Quiet End Theorem no longer bounds the odd moves; only the Periodicity Theorem does, usually far out, so winning moves can be enormous. In {8, 30, 34} the only winning move is 49,337.</p>`;
    }
    kinds.add(quiet);
    if (kinds.size === 2) markDone("quiet");
  }
  root.append(
    eyebrow("THE QUIET END THEOREM, WINNING WAYS (1982)"),
    el("h2", {}, "Quiet ends, short and long"),
    story("A <b>quiet ender</b> is an ender where the unpaid amounts pair up: for every k, exactly one of k and t − k is paid. George Sicherman's papers use these names.",
          "Pick a position and look at the pairs; try both a quiet one and {4, 5, 7}. The quiet ones are what make even positions <b>short</b>, so a computer can settle them by checking a finite list."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("label", { for: "quiet-pos" }, "Position"), sel), pairsBox, verdict, doubled),
  );
  setup(options[0]);
}

// ---------------------------------------------------------------- lesson 5: Sicherman's long position
// {8, 10, 22} is long: its half {4, 5, 11} is not a quiet ender, so every odd number stays a
// possible move. Each odd move x leaves a finite game, which the evaluator solves here.
const LONG = [8, 10, 22], LONG_MAX = 199;   // larger odd moves take seconds to solve in a browser
function longReply(x) {
  const s = new Engine([...LONG, x]);
  return { reply: s.winningMove(s.initialState), states: s.memo.size };
}
function lessonLong(root) {
  const msg = el("p", { class: "msg", "aria-live": "polite" }, "Pick an odd number.");
  const tiles = el("div", { class: "tiles" });
  const rows = el("tbody");
  const tried = new Map();
  const custom = el("input", { type: "number", min: "3", max: String(LONG_MAX), step: "2", value: "101", id: "long-x", "aria-label": `Any odd number up to ${LONG_MAX}` });
  const quiz = el("div", { class: "row" });
  const quizMsg = el("p", { class: "msg", "aria-live": "polite" });
  let predicted = 0;

  function name(x) {
    if (!(Number.isInteger(x) && x >= 3 && x <= LONG_MAX && x % 2)) { msg.className = "msg"; msg.textContent = `Choose an odd number from 3 to ${LONG_MAX}.`; return; }
    const { reply, states } = longReply(x);
    tried.set(x, reply);
    const dest = minimal([...LONG, x, reply]);
    msg.className = "msg lose";
    msg.textContent = `You name ${x}. The computer answers ${reply}, reaching ${setText(dest)}: a losing position for you (${plural(states, "position")} examined).`;
    rows.prepend(el("tr", {}, el("td", { class: "mono" }, x), el("td", { class: "mono" }, reply),
      el("td", { class: "mono" }, (reply > x ? "+" : "") + (reply - x))));
    draw();
    if (tried.size === 4) ask();
  }
  function draw() {
    const keep = focusedTile(tiles);
    tiles.replaceChildren();
    for (let x = 3; x <= 63; x += 2) {
      tiles.append(el("button", { class: "tile sm" + (tried.has(x) ? " bad" : ""), type: "button", "data-n": x,
        "aria-label": tried.has(x) ? `${x}, answered by ${tried.get(x)}` : String(x), onclick: () => name(x) }, x));
    }
    refocus(tiles, keep);
  }
  function ask() {
    const x = 2 * (50 + Math.floor(Math.random() * 50)) + 1;   // an odd number from 101 to 199
    const guess = el("input", { type: "number", min: "1", step: "1", id: "long-guess", "aria-label": `Your prediction for ${x}` });
    quiz.replaceChildren(el("label", { for: "long-guess" }, `Predict: what does the computer answer to ${x}?`), guess,
      el("button", { class: "ctrl primary", type: "button", onclick: (e) => check(x, Number(guess.value), e.currentTarget) }, "Check"));
    quizMsg.className = "msg"; quizMsg.textContent = "";
  }
  function check(x, y, button) {
    button.disabled = true;                 // the solve below runs on the page's thread
    const { reply } = longReply(x);
    let ok = y === reply;
    if (!ok && Number.isInteger(y) && y > 1) {
      const s = new Engine([...LONG, x]);
      if (!isPaid(s, s.initialState, y)) { const d = new Engine([...LONG, x, y]); ok = d.winningMove(d.initialState) === 0; }
    }
    quizMsg.className = "msg " + (ok ? "win" : "lose");
    quizMsg.textContent = ok ? (y === reply ? `Yes: the computer answers ${reply}.` : `Yes: ${y} also wins (the computer's first choice is ${reply}).`)
                             : `No: the computer answers ${reply}.`;
    if (ok && ++predicted >= 2) markDone("long");
    if (ok) setTimeout(ask, 1600); else button.disabled = false;
  }
  root.append(
    eyebrow("GEORGE SICHERMAN, 1990s"),
    el("h2", {}, "A long losing position"),
    story("Halve {8, 10, 22} and you get {4, 5, 11}. Its unpaid amounts are 1, 2, 3, 6 and 7, and they do not pair up: 1 and 6 are both unpaid. So {8, 10, 22} is <b>long</b>: no quiet end trims its odd moves, and every odd number from 3 up is still a legal move.",
          "George Sicherman proved it is a losing position anyway. Try to beat it: every odd move you name leaves a finite game, and the computer solves it on the spot."),
    el("div", { class: "game" }, tiles,
      el("div", { class: "row" }, el("label", { for: "long-x" }, `or any odd number up to ${LONG_MAX}`), custom,
         el("button", { class: "ctrl", type: "button", onclick: () => name(Number(custom.value)) }, "Name it")),
      msg,
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["you", "computer", "difference"].map((h) => el("th", {}, h)))), rows)),
      quiz, quizMsg),
    story("There are infinitely many odd moves, so trying them one by one can never finish. Sicherman used the <b>Periodicity Theorem</b>: when the named numbers have greatest common divisor 2, the analysis of the odd moves eventually repeats, so a finite computation covers them all. He ran it on a network of SUN workstations in the 1990s.",
          "In 2026 the campaign's periodicity engine checked his result independently: from 49 on, its analysis repeats every 8, and no odd move wins. He wrote that he was “relieved to learn that your results agree with mine.”"),
  );
  draw();
}

// ---------------------------------------------------------------- lesson 6: Blok's mirror
// Blok's pairing for the unpaid amounts of {8, 12} (checked in sylver/eight_twelve.py):
// 2 with 3, 4 with 6, 4j+1 with 4j+3 and 8j+2 with 8j+6 for j >= 1; 1 has no mate.
function mirrorMate(x) {
  if (x === 1) return null;
  if (x === 2 || x === 3) return 5 - x;
  if (x === 4 || x === 6) return 10 - x;
  if (x % 2) return x % 4 === 1 ? x + 2 : x - 2;
  return x % 8 === 2 ? x + 4 : x - 4;
}
const MIRROR_TOP = 63, MIRROR_LIMIT = 1200;
function lessonMirror(root) {
  let named, paid, over, mode, game = 0;
  const msg = el("p", { class: "msg", "aria-live": "polite" });
  const board = el("div", { class: "tiles mirror" });
  const pairs = el("p", { class: "note" });
  const modes = el("div", { class: "row" });
  const big = el("input", { type: "number", min: "1", max: "999", value: "101", id: "mirror-x", "aria-label": "Any unpaid number up to 999" });
  const unpaid = () => { const out = []; for (let n = 1; n <= MIRROR_LIMIT - 8; n++) if (!paid[n]) out.push(n); return out; };
  const recount = () => { paid = paidUpTo([8, 12, ...named], MIRROR_LIMIT); };
  const later = (f, ms) => { const mine = game; setTimeout(() => { if (mine === game) f(); }, ms); };
  function start(m) {
    game++;
    mode = m; named = []; over = false; recount();
    msg.className = "msg";
    msg.textContent = mode === "beat" ? "Your move: name any unpaid amount. The mirror answers." : "The computer moves first. Answer with the mate.";
    draw();
    if (mode === "hold") later(computerMoves, 500);
  }
  function play(x) { named.push(x); recount(); }
  function finished(loser) {
    over = true;
    msg.className = "msg " + (loser === "you" ? "lose" : "win");
    msg.textContent = loser === "you" ? "Only 1 is left, and it is your turn: the mirror wins, as Blok's proof promises."
                                      : "Only 1 is left for the computer. You held the mirror and won.";
    markDone("mirror");
    draw();
  }
  function youName(x) {
    if (over) return;
    if (mode === "beat") {
      if (x === 1) { finished("you"); return; }
      play(x);
      const y = mirrorMate(x);
      play(y);
      msg.className = "msg";
      msg.textContent = `You name ${x}. The mirror answers ${y}, its mate.`;
      if (unpaid().length === 1) finished("you"); else draw();
      return;
    }
    const want = mirrorMate(named[named.length - 1]);
    if (x !== want) { msg.className = "msg lose"; msg.textContent = `${x} is not the mate of ${named[named.length - 1]}. Look for the pair.`; return; }
    play(x);
    if (unpaid().length === 1) { finished("computer"); return; }
    msg.className = "msg win"; msg.textContent = `Right: ${x} pairs with ${named[named.length - 2]}.`;
    draw();
    later(computerMoves, 900);
  }
  function computerMoves() {
    if (over) return;
    const live = unpaid().filter((n) => n > 1), small = live.filter((n) => n <= MIRROR_TOP);
    const options = small.length ? small : live;
    const x = options[Math.floor(Math.random() * options.length)];
    play(x);
    msg.className = "msg"; msg.textContent = `The computer names ${x}. Which number is its mate?`;
    draw();
  }
  function draw() {
    const keep = focusedTile(board);
    board.replaceChildren();
    for (let n = 1; n <= MIRROR_TOP; n++) {
      const isNamed = n === 8 || n === 12 || named.includes(n);
      const mate = mirrorMate(n);
      let cls = "tile";
      if (isNamed) cls += " named"; else if (paid[n]) cls += " paid"; else if (n === 1) cls += " one";
      board.append(el("button", { class: cls, type: "button", "data-n": n, disabled: isNamed || paid[n] || over,
        "aria-label": paid[n] ? `${n} paid` : mate ? `${n}, mate ${mate}` : String(n), onclick: () => youName(n) },
        el("span", {}, n), !paid[n] && !isNamed && mate ? el("span", { class: "tag" }, "↔" + mate) : null));
    }
    refocus(board, keep);
    const live = unpaid();
    const finite = live[live.length - 1] < MIRROR_LIMIT - 64;
    const shown = live.filter((n) => n > 1 && n < mirrorMate(n)).slice(0, 12).map((n) => `${n}–${mirrorMate(n)}`);
    pairs.textContent = !shown.length ? "Unpaid: only 1." : `Unpaid: 1, and the pairs ${shown.join(", ")}` +
      (finite ? (live.length - 1 > 2 * shown.length ? ", …" : ".") : ", … and infinitely many more.");
  }
  [["beat", "Try to beat the mirror"], ["hold", "Hold the mirror yourself"]].forEach(([m, label], i) =>
    modes.append(el("button", { class: "chip", type: "button", "aria-pressed": String(i === 0), onclick: (e) => {
      modes.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      e.currentTarget.setAttribute("aria-pressed", "true"); start(m); } }, label)));
  root.append(
    eyebrow("THOMAS BLOK, 2021"),
    el("h2", {}, "Blok's mirror"),
    story("By 2002 {8, 12} was known to be a losing position: Sicherman's paper lists it, with the family {8, 12, 8n + 2, 8n + 6}. Thomas Blok's 2021 report on positions with g = 2 shows that a simple <b>pairing strategy</b> proves it. The unpaid amounts of {8, 12} are 4, every odd number, and every number 2 more than a multiple of 4.",
          "Blok pairs them: 2 with 3, 4 with 6, 5 with 7, 9 with 11 and so on, and 10 with 14, 18 with 22 and so on. Whatever the first player names, the second names its mate. The mate is always still unpaid, the unpaid amounts always come in whole pairs, and in the end the first player must name 1."),
    el("div", { class: "game" }, modes, board,
      el("div", { class: "row" }, el("label", { for: "mirror-x" }, "or name a larger number"), big,
         el("button", { class: "ctrl", type: "button", onclick: () => {
           const x = Number(big.value);
           if (!Number.isInteger(x) || x < 1 || x > 999 || paid[x]) { msg.className = "msg"; msg.textContent = "Choose an unpaid number up to 999."; return; }
           youName(x);
         } }, "Name it")),
      pairs, msg),
    el("p", { class: "note" }, "Each tile shows its mate. The board stops at 63, but the pairs go on forever."),
  );
  start("beat");
}

// ---------------------------------------------------------------- lesson 7: answer the reply
// Certified losing positions the answer lesson names (sylver/short_certificates.py and the campaign audits).
const NAMED = {
  C: [4, 6], E: [8, 14], F: [12, 14, 16], G: [8, 20, 26], I: [16, 20, 22, 24], K: [10, 16, 24], P0: [12, 16, 22],
  R: [14, 16, 20, 26], T: [16, 20, 34], U: [16, 26, 88], V: [16, 26, 36, 56], W: [16, 26, 62, 98], Y: [16, 28, 58],
  Z: [16, 30, 56], "Z′": [16, 30, 40, 44], B24: [16, 24, 38, 44], B28: [16, 28, 38, 40],
};
// One row per legal even reply r to 16 up to 36: the certified answer, where it leads, why that position loses,
// its generators when it is finite (so the page can check it), and three moves that are NOT answers, each with
// the computer's winning reply and, when it has one, the name of the certified losing position that reply reaches.
const TABLE = [
  [2, 3, "{2, 3}", "finite: only 1 is left", [2, 3], [[5, 3, null], [7, 3, null], [9, 3, null]]],
  [4, 6, "{4, 6}", "C, a classic losing position", null, [[3, 2, null], [5, 11, null], [10, 6, "C"]]],
  [6, 7, "{6, 7, 16}", "finite", [6, 7, 16], [[5, 19, null], [8, 4, "C"], [9, 13, null]]],
  [8, 14, "{8, 14}", "E, a short losing position", null, [[4, 6, "C"], [9, 21, null], [22, 14, "E"]]],
  [10, 9, "{9, 10, 16}", "finite", [9, 10, 16], [[6, 4, "C"], [7, 19, null], [34, 24, "K"]]],
  [12, 14, "{12, 14, 16}", "F, a short losing position", null, [[5, 9, null], [26, 14, "F"], [34, 22, "P0"]]],
  [14, 8, "{8, 14}", "16 = 8 + 8, so this is E = {8, 14}", null, [[5, 27, null], [20, 26, "R"], [22, 8, "E"]]],
  [18, 5, "{5, 16, 18}", "finite", [5, 16, 18], [[4, 6, "C"], [7, 6, null], [9, 10, null]]],
  [20, 34, "{16, 20, 34}", "T, on Sicherman's list of losing positions, certified in 2026", null, [[9, 6, null], [10, 24, "K"], [22, 24, "I"]]],
  [22, 12, "{12, 16, 22}", "P0, a published losing position", null, [[8, 14, "E"], [13, 5, null], [20, 24, "I"]]],
  [24, 10, "{10, 16, 24}", "K, listed by Sicherman in 2002 and in Blok's g = 2 report, certified in 2026", null, [[9, 7, null], [22, 12, "P0"], [38, 44, "B24"]]],
  [26, 88, "{16, 26, 88}", "U, certified in 2026", null, [[11, 40, null], [36, 56, "V"], [62, 98, "W"]]],
  [28, 58, "{16, 28, 58}", "Y, certified in 2026", null, [[13, 51, null], [38, 40, "B28"], [74, 58, "Y"]]],
  [30, 56, "{16, 30, 56}", "Z, certified in 2026", null, [[11, 39, null], [40, 44, "Z′"], [72, 56, "Z"]]],
  [34, 20, "{16, 20, 34}", "T again, reached the other way", null, [[13, 19, null], [22, 12, "P0"], [36, 20, "T"]]],
  [36, 23, "{16, 23, 36}", "finite: 1,179,780 positions", null, [[15, 7, null], [26, 56, "V"], [34, 20, "T"]]],
];
function lessonAnswer(root) {
  let i = 0, score = 0, seen = 0;
  const q = el("div", { class: "story" }), opts = el("div", { class: "row" }), msg = el("p", { class: "msg", "aria-live": "polite" });
  const after = el("div", { class: "row" }), checked = el("p", { class: "note", "aria-live": "polite" });
  function ask(focus) {
    const [r, ans, , , , wrong] = TABLE[i];
    q.innerHTML = `<p>Reply ${i + 1} of ${TABLE.length}. You opened with <b>16</b>. The computer replies <b>${r}</b>. Which answer leaves a losing position for it?</p>`;
    const list = [ans, ...wrong.map(([x]) => x)].sort((x, y) => x - y);
    opts.replaceChildren(...list.map((x) => el("button", { class: "tile", type: "button", onclick: () => answer(x) }, x)));
    msg.className = "msg"; msg.textContent = ""; checked.textContent = ""; after.replaceChildren();
    if (focus) opts.querySelector("button").focus();
  }
  function answer(x) {
    const [r, ans, dest, why, finite, wrong] = TABLE[i];
    seen++;
    opts.querySelectorAll("button").forEach((b) => { b.disabled = true; if (Number(b.textContent) === ans) b.classList.add("good"); else if (Number(b.textContent) === x) b.classList.add("bad"); });
    if (x === ans) { score++; msg.className = "msg win"; msg.textContent = `Yes: ${r} is answered by ${ans}, reaching ${dest} (${why}).`; }
    else {
      const [, y, name] = wrong.find(([w]) => w === x);
      const reached = setText(minimal([16, r, x, y]));
      msg.className = "msg lose";
      msg.textContent = `Not ${x}: after 16, ${r} and ${x}, the computer names ${y} and reaches ${name ? `${name} = ${reached}` : reached}, a losing position for you. ` +
                        `The certified answer is ${ans}, reaching ${dest} (${why}).`;
    }
    if (finite) after.append(el("button", { class: "ctrl", type: "button", onclick: (e) => {
      const s = new Engine(finite), w = s.winningMove(s.initialState);
      e.currentTarget.remove();
      checked.textContent = w === 0 ? `Checked here: ${dest} is a losing position for the player to move (${plural(s.memo.size, "position")} examined).` : `Unexpected: ${dest} has the winning move ${w}.`;
    } }, `Check ${dest} yourself`));
    const last = i === TABLE.length - 1;
    after.append(el("button", { class: "ctrl primary", type: "button", onclick: () => {
      if (!last) { i++; ask(true); return; }
      q.innerHTML = `<p>All ${TABLE.length} replies done: you found ${score} of ${seen} answers.</p>`;
      opts.replaceChildren(); msg.className = "msg win"; msg.textContent = "Every even reply up to 36 has a certified answer. The next one, 38, has none yet: see the last lesson.";
      checked.textContent = "";
      after.replaceChildren(el("button", { class: "ctrl", type: "button", onclick: () => { i = 0; score = 0; seen = 0; ask(true); } }, "Start again"));
      markDone("answer");
      after.querySelector("button").focus();
    } }, last ? "Finish" : "Next reply"));
    after.querySelector(".primary").focus();
  }
  root.append(
    eyebrow("THE OPENING 16, 1982–2026"),
    el("h2", {}, "Answer the reply"),
    story("Nobody knows who wins after the opening 16. One way to show the opener wins is to answer every reply. A reply r <b>loses</b> when the opener has an answer a that leaves {16, r, a} as a losing position.",
          "Odd replies lose by Hutchings' theorem. The even replies up to 36 now all have certified answers. Find them. Some replies have more than one answer; the three wrong choices offered here are certainly wrong."),
    el("div", { class: "game" }, q, opts, msg, after, checked),
  );
  ask(false);
}

// ---------------------------------------------------------------- lesson 8: assay a certificate
// The even obligations of E = {8, 14} and their replies, as in node E of sylver/short_certificates.py.
const E_REPLIES = { 2: [3, null], 4: [6, "C = {4, 6}"], 6: [4, "C = {4, 6}"], 10: [19, null], 12: [10, "{8, 10, 12, 14}, a member of the pairing family"],
                    18: [25, null], 20: [9, null], 26: [17, null], 34: [27, null] };
function lessonAssay(root) {
  // E = {8,14}: half {4,7}, t = 17. Even obligations 2g for the gaps g; odd obligations the odd gaps above 1.
  const half = [4, 7], t = 17, pay = paidUpTo(half, t), gaps = [];
  for (let n = 1; n <= t; n++) if (!pay[n]) gaps.push(n);
  const obligations = [...gaps.map((g) => 2 * g), ...gaps.filter((g) => g > 1 && g % 2)].sort((a, b) => a - b);
  const tbody = el("tbody"), msg = el("p", { class: "msg", "aria-live": "polite" });
  const rows = obligations.map((m) => {
    const node = m % 2 === 0 ? E_REPLIES[m] : null;
    const status = el("span", { class: "status s-run" }, node && node[1] ? "named position" : "not checked");
    const reply = el("td", { class: "mono" }, node ? String(node[0]) : "?");
    const dest = el("td", { class: "mono" }, node ? (node[1] || setText(minimal([8, 14, m, node[0]]))) : "");
    const tr = el("tr", {}, el("td", { class: "mono" }, m), el("td", {}, m % 2 ? "odd" : "even"), reply, dest, el("td", {}, status));
    tbody.append(tr);
    return { m, node, status, reply, dest };
  });
  async function assay() {
    let ok = 0;
    for (const r of rows) {
      await new Promise((res) => setTimeout(res, 60));
      if (r.node && r.node[1]) { r.status.className = "status s-node"; r.status.textContent = "certified position"; ok++; continue; }
      const child = [8, 14, r.m];
      let w = r.node ? r.node[0] : null;
      if (w === null) { const s = new Engine(child); w = s.winningMove(s.initialState); }
      const dest = minimal([...child, w]), s2 = new Engine(dest), res = s2.winningMove(s2.initialState);
      r.reply.textContent = String(w); r.dest.textContent = setText(dest);
      if (res === 0) { r.status.className = "status s-ok"; r.status.textContent = `P, ${plural(s2.memo.size, "position")}`; ok++; }
      else { r.status.className = "status s-bad"; r.status.textContent = "fails"; }
    }
    msg.className = "msg " + (ok === rows.length ? "win" : "lose");
    msg.textContent = ok === rows.length ? `All ${rows.length} obligations are covered, so {8, 14} is a losing position.` : "Some obligation failed.";
    if (ok === rows.length) markDone("assay");
  }
  root.append(
    eyebrow("HOW 2026 CERTIFICATES WORK"),
    el("h2", {}, "Assay a certificate"),
    story("To prove a short position is losing, you list its <b>obligations</b>, the only moves the Quiet End Theorem leaves open, and answer each one with a reply that reaches a known losing position.",
          "{8, 14} is the double of the quiet ender {4, 7}. It has 14 obligations. The computer below finds or checks each reply. In the 2026 campaign the same kind of check ran on positions with hundreds of millions of states, twice, by two independent programs."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("button", { class: "ctrl primary", type: "button", onclick: (e) => { e.currentTarget.disabled = true; assay(); } }, "Assay all 14")),
       el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["move", "kind", "reply", "reaches", "check"].map((h) => el("th", {}, h)))), tbody)), msg),
  );
}

// ---------------------------------------------------------------- lesson 9: the frontier
// Every obligation of {16, 38}: k is the kind of move, s its status in the reply-38 record of October 9, 2026
// (sylver/campaigns/r38-2026-10-09); tests/test_docs_mint.py derives the same statuses from its scan logs.
const FRONTIER = [
  {"m": 2, "k": "long", "s": "search", "why": "{16,38,2} is won by 3 (search)"},
  {"m": 3, "k": "odd", "s": "search", "why": "{16,38,3} has a winning reply (the ledger's scan)"},
  {"m": 4, "k": "short", "s": "certified", "why": "{16,38,4} moves by 6 to C={4,6}, a certified losing position"},
  {"m": 5, "k": "odd", "s": "search", "why": "{16,38,5} has a winning reply (the ledger's scan)"},
  {"m": 6, "k": "short", "s": "certified", "why": "{16,38,6} moves by 4 to C={4,6}, a certified losing position"},
  {"m": 7, "k": "odd", "s": "search", "why": "{16,38,7} has a winning reply (the ledger's scan)"},
  {"m": 8, "k": "short", "s": "certified", "why": "{16,38,8} moves by 14 to E={8,14}, a certified losing position"},
  {"m": 9, "k": "odd", "s": "search", "why": "{16,38,9} has a winning reply (the ledger's scan)"},
  {"m": 10, "k": "long", "s": "search", "why": "{16,38,10} is won by 9 (search)"},
  {"m": 11, "k": "odd", "s": "search", "why": "{16,38,11} has a winning reply (the ledger's scan)"},
  {"m": 12, "k": "short", "s": "certified", "why": "{16,38,12} moves by 14 to F={12,14,16}, a certified losing position"},
  {"m": 13, "k": "odd", "s": "search", "why": "{16,38,13} has a winning reply (the ledger's scan)"},
  {"m": 14, "k": "long", "s": "certified", "why": "{16,38,14} moves by 8 to E={8,14}, a certified losing position"},
  {"m": 15, "k": "odd", "s": "search", "why": "{16,38,15} has a winning reply (the ledger's scan)"},
  {"m": 17, "k": "odd", "s": "search", "why": "{16,38,17} has a winning reply (the ledger's scan)"},
  {"m": 18, "k": "long", "s": "search", "why": "{16,38,18} is won by 5 (search)"},
  {"m": 20, "k": "short", "s": "search", "why": "{16,38,20} is won by the odd move 13 (search)"},
  {"m": 21, "k": "odd", "s": "search", "why": "{16,38,21} has a winning reply (the ledger's scan)"},
  {"m": 22, "k": "short", "s": "certified", "why": "{16,38,22} moves by 12 to P0={12,16,22}, a certified losing position"},
  {"m": 23, "k": "odd", "s": "search", "why": "{16,38,23} has a winning reply (the ledger's scan)"},
  {"m": 24, "k": "short", "s": "certified", "why": "{16,38,24} moves by 44 to B24={16,24,38,44}, a certified losing position"},
  {"m": 25, "k": "odd", "s": "search", "why": "{16,38,25} has a winning reply (the ledger's scan)"},
  {"m": 26, "k": "long", "s": "search", "why": "{16,38,26} is won by 97 (search)"},
  {"m": 28, "k": "short", "s": "certified", "why": "{16,38,28} moves by 40 to B28={16,28,38,40}, a certified losing position"},
  {"m": 29, "k": "odd", "s": "search", "why": "{16,38,29} has a winning reply (the ledger's scan)"},
  {"m": 30, "k": "long", "s": "search", "why": "{16,38,30} is won by 271 (search)"},
  {"m": 31, "k": "odd", "s": "search", "why": "{16,38,31} has a winning reply (the ledger's scan)"},
  {"m": 33, "k": "odd", "s": "search", "why": "{16,38,33} has a winning reply (the ledger's scan)"},
  {"m": 34, "k": "long", "s": "search", "why": "{16,38,34} is won by 53 (search)"},
  {"m": 36, "k": "long", "s": "search", "why": "{16,38,36} is won by 123 (search)"},
  {"m": 37, "k": "odd", "s": "search", "why": "{16,38,37} has a winning reply (the ledger's scan)"},
  {"m": 39, "k": "odd", "s": "search", "why": "{16,38,39} has a winning reply (the ledger's scan)"},
  {"m": 40, "k": "short", "s": "certified", "why": "{16,38,40} moves by 28 to B28={16,28,38,40}, a certified losing position"},
  {"m": 41, "k": "odd", "s": "search", "why": "{16,38,41} has a winning reply (the ledger's scan)"},
  {"m": 42, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 44, "k": "short", "s": "certified", "why": "{16,38,44} moves by 24 to B24={16,24,38,44}, a certified losing position"},
  {"m": 45, "k": "odd", "s": "search", "why": "{16,38,45} has a winning reply (the ledger's scan)"},
  {"m": 46, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 47, "k": "odd", "s": "search", "why": "{16,38,47} has a winning reply (the ledger's scan)"},
  {"m": 49, "k": "odd", "s": "search", "why": "{16,38,49} has a winning reply (the ledger's scan)"},
  {"m": 50, "k": "long", "s": "search", "why": "{16,38,50} is won by 79 (search)"},
  {"m": 52, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 53, "k": "odd", "s": "search", "why": "{16,38,53} has a winning reply (the ledger's scan)"},
  {"m": 55, "k": "odd", "s": "search", "why": "{16,38,55} has a winning reply (the ledger's scan)"},
  {"m": 56, "k": "short", "s": "certified", "why": "{16,38,56} moves by 60 to B56={16,38,56,60}, a certified losing position"},
  {"m": 58, "k": "long", "s": "search", "why": "{16,38,58} is won by 11 (search)"},
  {"m": 60, "k": "short", "s": "search", "why": "{16,38,60} is won by the odd move 17 (search)"},
  {"m": 61, "k": "odd", "s": "search", "why": "{16,38,61} has a winning reply (the ledger's scan)"},
  {"m": 62, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 63, "k": "odd", "s": "search", "why": "{16,38,63} has a winning reply (the ledger's scan)"},
  {"m": 66, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 68, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 69, "k": "odd", "s": "search", "why": "{16,38,69} is won by 25 (search)"},
  {"m": 71, "k": "odd", "s": "search", "why": "{16,38,71} is won by 73 (search)"},
  {"m": 72, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its hard long children have no witness yet"},
  {"m": 74, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 77, "k": "odd", "s": "search", "why": "{16,38,77} is won by 27 (search)"},
  {"m": 78, "k": "long", "s": "search", "why": "{16,38,78} is won by 27 (search)"},
  {"m": 79, "k": "odd", "s": "search", "why": "{16,38,79} is won by 50 (search)"},
  {"m": 82, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 84, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 85, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 87, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 88, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its obligation 72 leads back to {16,38,72}, so it waits on 72"},
  {"m": 90, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 93, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 94, "k": "long", "s": "search", "why": "{16,38,94} is won by 43 (search)"},
  {"m": 98, "k": "long", "s": "search", "why": "{16,38,98} is won by 31 (search)"},
  {"m": 100, "k": "long", "s": "search", "why": "{16,38,100} is won by 41 (search)"},
  {"m": 101, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 104, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; some of its odd obligations are not finished"},
  {"m": 106, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 109, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 110, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 116, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 117, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 120, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; some of its odd obligations are not finished"},
  {"m": 122, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 125, "k": "odd", "s": "open", "why": "open: the shared sweep stopped during 85 at its 1.4-billion-state cap"},
  {"m": 126, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 132, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 136, "k": "short", "s": "search", "why": "{16,38,136} is won by the odd move 37 (search)"},
  {"m": 138, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 142, "k": "long", "s": "open", "why": "open within the sweeps' state caps"},
  {"m": 148, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 154, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 158, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 164, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 170, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 174, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 180, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 186, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 196, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 202, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 212, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 218, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 234, "k": "long", "s": "open", "why": "not searched yet"},
  {"m": 250, "k": "long", "s": "open", "why": "not searched yet"},
];
function lessonFrontier(root) {
  const detail = el("p", { class: "detail", "aria-live": "polite" }, "Click a tile to see what is known about it.");
  const groups = [["odd", "Odd answers"], ["short", "Even answers that leave a short position"], ["long", "Even answers that leave a long position"]];
  const box = el("div", { class: "game" });
  const cls = { certified: "bad out", search: "paid out", open: "", ladder: "gold" };
  const label = { certified: "ruled out, certified", search: "ruled out by search", open: "open", ladder: "ladder rung" };
  const looked = new Set();
  for (const [k, title] of groups) {
    const tiles = el("div", { class: "tiles" });
    FRONTIER.filter((r) => r.k === k).forEach((r) => tiles.append(el("button", { class: "tile sm " + cls[r.s], type: "button",
      "aria-label": `${r.m}, ${label[r.s]}`, onclick: () => {
        detail.innerHTML = `<b>${r.m}</b> (${label[r.s]}): ${r.why}.`;
        looked.add(r.m);
        if (looked.size === 3) markDone("frontier");
      } }, r.m)));
    box.append(el("p", { class: "note" }, title), tiles);
  }
  const counts = (s) => FRONTIER.filter((r) => r.s === s).length;
  box.append(el("div", { class: "legend" },
    el("span", {}, el("i", { style: "border-color: var(--oxide); background: var(--oxide-soft)" }), `ruled out, certified (${counts("certified")})`),
    el("span", {}, el("i", { style: "border-color: transparent; background: var(--paid)" }), `ruled out by search (${counts("search")})`),
    el("span", {}, el("i", { style: "border-color: var(--gilt); background: var(--gilt-soft)" }), `ladder rungs (${counts("ladder")})`),
    el("span", {}, el("i", { style: "border-color: var(--copper); background: var(--copper-soft)" }), `open (${counts("open")})`)), detail);
  root.append(
    eyebrow("OCTOBER 2026"),
    el("h2", {}, "The frontier: the reply 38"),
    story("Every even reply to 16 up to 36 has an answer. The reply 38 does not, yet. Because {16, 38} is short, any answer must be one of these 98 moves.",
          "Eleven are ruled out by certified losing positions, and search has ruled out 44 more (struck through). The short candidates 72, 88, 104 and 120 form a <b>ladder</b> with 56 and 136: each rung leads back to the rungs below it, so at most one can be the answer."),
    box,
    el("p", { class: "note" }, "Status as of October 9, 2026, from the reply-38 record (sylver/campaigns/r38-2026-10-09 at github.com/rudi-cilibrasi/sylver-coinage). Search results are discovery output, not certificates."),
  );
}

// ---------------------------------------------------------------- navigation
const LESSONS = [
  ["play", "Mint and lose", "Conway's game", lessonPlay],
  ["sylvester", "The largest unpayable amount", "Sylvester, 1884", lessonSylvester],
  ["enders", "Steal a strategy", "Hutchings, 1982", lessonEnders],
  ["quiet", "Quiet ends, short and long", "Winning Ways", lessonQuiet],
  ["long", "A long losing position", "Sicherman, 1990s", lessonLong],
  ["mirror", "Blok's mirror", "Blok, 2021", lessonMirror],
  ["answer", "Answer the reply", "Opening 16", lessonAnswer],
  ["assay", "Assay a certificate", "2026", lessonAssay],
  ["frontier", "The frontier: 38", "October 2026", lessonFrontier],
];
let current = 0;
function renderNav() {
  const ol = document.getElementById("lessons");
  ol.replaceChildren(...LESSONS.map(([id, title, who], i) => el("li", {}, el("button", {
    class: "lesson-btn" + (done.has(id) ? " done" : ""), type: "button", "aria-current": i === current ? "page" : null,
    onclick: () => show(i, true) }, el("span", { class: "num" }, i + 1), el("span", { class: "lt" }, el("b", {}, title), el("span", {}, who))))));
}
function show(i, focus) {
  current = i;
  const main = document.getElementById("main");
  main.replaceChildren();
  LESSONS[i][3](main);
  if (i < LESSONS.length - 1) main.append(el("div", { class: "next" }, el("button", { class: "ctrl primary", type: "button", onclick: () => show(i + 1, true) }, `Next: ${LESSONS[i + 1][1]}`)));
  renderNav();
  // on phones the lesson list scrolls sideways: bring the current lesson into it (the page itself does not move)
  const list = document.getElementById("lessons"), here = list.querySelector('.lesson-btn[aria-current="page"]');
  if (here) list.scrollLeft += here.getBoundingClientRect().left - list.getBoundingClientRect().left - 16;
  try { history.replaceState(null, "", "#" + LESSONS[i][0]); } catch (e) { /* not allowed here */ }
  if (focus) main.focus({ preventScroll: false });
}
const lessonFromHash = () => LESSONS.findIndex(([id]) => "#" + id === location.hash);

if (typeof module !== "undefined") {
  module.exports = { E_REPLIES, FRONTIER, LESSONS, LONG, LONG_MAX, NAMED, TABLE, isPaid, minimal, mirrorMate, paidUpTo };
} else {
  window.addEventListener("hashchange", () => { const i = lessonFromHash(); if (i >= 0 && i !== current) show(i, false); });
  show(Math.max(0, lessonFromHash()), false);
}
