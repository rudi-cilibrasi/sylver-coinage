// The Sylver Mint: seven small games that retrace the history of Sylver
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
  let solver, state, history, human, over, hints = false;
  const msg = el("p", { class: "msg", "aria-live": "polite" });
  const board = el("div", { class: "tiles" });
  const picks = el("div", { class: "row" });
  const hintBtn = el("button", { class: "ctrl", type: "button", "aria-pressed": "false",
    onclick: () => { hints = !hints; hintBtn.setAttribute("aria-pressed", String(hints)); draw(); } }, "Show winning moves");
  const undo = el("button", { class: "ctrl", type: "button", onclick: () => {
    if (history.length >= 2 && !over) { history.pop(); history.pop(); state = recompute(); draw(); }
  } }, "Undo");
  const named = () => history.map((h) => h.m);
  function recompute() { let s = solver.initialState; for (const h of history) s = solver.adjoin(s, h.m); return s; }
  function start(gens, humanFirst) {
    solver = new Engine(gens); history = []; over = false; human = humanFirst;
    state = solver.initialState;
    msg.className = "msg";
    msg.textContent = humanFirst ? "Your move. Pick an unpaid amount." : "The computer moves first.";
    draw();
    if (!humanFirst) setTimeout(computer, 500);
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
    if (m === 1) { end(who === "you" ? "you" : "computer", unpaid().length > 1); return; }
    state = solver.adjoin(state, m);
    if (unpaid().length === 1) { end(who === "you" ? "computer" : "you"); return; }
    draw();
  }
  function computer() {
    if (over) return;
    const w = solver.winningMove(state), legal = solver.legalMoves(state);
    const m = w || (legal.length ? legal[legal.length - 1] : 1);
    msg.className = "msg";
    msg.textContent = `The computer names ${m}.` + (w ? "" : " (It is losing, so it plays for time.)");
    move(m, "computer");
  }
  function draw() {
    board.replaceChildren();
    const gens = solver.gens, top = solver.frobenius;
    const winSet = new Set();
    if (hints && !over) for (const m of solver.legalMoves(state)) if (solver.winningMove(solver.adjoin(state, m)) === 0) winSet.add(m);
    for (let n = 1; n <= top; n++) {
      const isNamed = gens.includes(n) || named().includes(n);
      const paid = isPaid(solver, state, n) && n !== 1;
      let cls = "tile";
      if (isNamed) cls += " named"; else if (paid) cls += " paid";
      else if (n === 1) cls += " one";
      else if (hints && !over) cls += winSet.has(n) ? " good" : " bad";
      const b = el("button", { class: cls, type: "button", disabled: isNamed || paid || over,
        "aria-label": `${n}${paid ? " paid" : ""}`, onclick: () => { move(n, "you"); if (!over) setTimeout(computer, 450); } }, n);
      board.append(b);
    }
  }
  presets.forEach((g, i) => picks.append(el("button", { class: "chip", type: "button", "aria-pressed": String(i === 0),
    onclick: (e) => { picks.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      e.currentTarget.setAttribute("aria-pressed", "true"); start(g, true); } }, "start at " + setText(g))));
  root.append(
    el("p", { class: "eyebrow" }, "LESSON 1 · JOHN H. CONWAY'S GAME"),
    el("h2", {}, "Mint and lose"),
    story("Two players take turns naming a positive whole number. A number is <b>paid</b> once it is a sum of numbers already named, and paid numbers can never be named again. Whoever is forced to name <b>1</b> loses.",
          "The two silver coins are already named. Copper tiles are the amounts still unpaid, and grey tiles are paid. You move first, and the computer plays perfectly."),
    el("div", { class: "game" }, picks, board, msg, el("div", { class: "row" }, hintBtn, undo)),
    el("p", { class: "note" }, "Every position like these, with two coins that share no factor, is a win for the player to move, so a winning move always exists. Finding it is the hard part."),
  );
  start(presets[0], true);
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
        onclick: () => { marked.has(n) ? marked.delete(n) : marked.add(n); draw(); } }, n));
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
    el("p", { class: "eyebrow" }, "LESSON 2 · J. J. SYLVESTER, 1884"),
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
      board.append(el("button", { class: cls, type: "button", onclick: () => explain(n) }, n));
    }
  }
  function explain(u) {
    const pay = paidUpTo(gens, t);
    if (u === t) { msg.className = "msg"; msg.innerHTML = `${t} is the one move that removes nothing else: it is the <i>end</i>.`; return; }
    if (u === 1) { msg.className = "msg lose"; msg.textContent = "Naming 1 loses at once."; tried.add(1); draw(); return; }
    tried.add(u);
    msg.className = "msg";
    msg.innerHTML = `Naming ${u} pays ${t}: ${t} = ${u} + ${t - u}, and ${t - u} ${pay[t - u] ? "is already paid" : "is paid too"}.`;
    const left = [];
    for (let n = 2; n < t; n++) if (!pay[n] && !tried.has(n)) left.push(n);
    if (!left.length) finish();
    draw();
  }
  function finish() {
    const s = new Engine(gens), w = s.winningMove(s.initialState);
    reveal.innerHTML = `Every move except ${t} also pays ${t}, so ${setText(gens)} is an <b>ender</b>. Suppose naming ${t} lost to some reply u. Then naming u first would reach the same position and win. Either way the player to move can win. Here the computer finds the winning move: <b>${w}</b>.`;
    markDone("enders");
  }
  root.append(
    el("p", { class: "eyebrow" }, "LESSON 3 · HUTCHINGS' THEOREM, IN WINNING WAYS (1982)"),
    el("h2", {}, "Steal a strategy"),
    story("R. L. Hutchings showed that every position made of two coins with no common factor is an <b>ender</b>: every legal move except the largest unpaid amount t also pays t.",
          "A strategy-stealing argument then shows the player to move must be able to win. After the opening 5, 7, 11, 13 or any larger prime, every reply leaves such a position, so a prime opening wins. The proof names no winning move."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("label", { for: "end-pair" }, "Try"), sel), board, msg, reveal),
  );
  setup(options[1]);
  sel.value = options[1].join(",");
}

// ---------------------------------------------------------------- lesson 4: quiet ends
function lessonQuiet(root) {
  const options = [[4, 7], [5, 6], [4, 5, 7], [6, 8, 11], [8, 10, 11, 12], [4, 6, 9]];
  let gens, t;
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
      if (g.join() === "4,7") markDone("quiet");
    } else {
      doubled.innerHTML = `<p>Doubling an unquiet position gives a <b>long</b> one: no theorem bounds the odd moves, and winning moves can be enormous. In {8, 30, 34} the only winning move is 49,337.</p>`;
    }
  }
  root.append(
    el("p", { class: "eyebrow" }, "LESSON 4 · THE QUIET END THEOREM, WINNING WAYS (1982)"),
    el("h2", {}, "Quiet ends, short and long"),
    story("A <b>quiet ender</b> is an ender where the unpaid amounts pair up: for every k, exactly one of k and t − k is paid. George Sicherman's papers use these names.",
          "Pick a position and look at the pairs. The quiet ones are what make even positions <b>short</b>, so a computer can settle them by checking a finite list."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("label", { for: "quiet-pos" }, "Position"), sel), pairsBox, verdict, doubled),
  );
  setup(options[0]);
}

// ---------------------------------------------------------------- lesson 5: answer the reply
const TABLE = [
  [2, 3, "{2, 3}", "finite: only 1 is left", [2, 3]], [4, 6, "{4, 6}", "Winning Ways: a losing position", null],
  [6, 7, "{6, 7, 16}", "finite", [6, 7, 16]], [8, 14, "{8, 14}", "a short losing position", null],
  [10, 9, "{9, 10, 16}", "finite", [9, 10, 16]], [12, 14, "{12, 14, 16}", "a short losing position", null],
  [14, 8, "{8, 14}", "16 = 8 + 8, so this is {8, 14}", null], [18, 5, "{5, 16, 18}", "finite", [5, 16, 18]],
  [20, 34, "{16, 20, 34}", "on Sicherman's list of losing positions, certified in 2026", null], [22, 12, "{12, 16, 22}", "a published losing position", null],
  [24, 10, "{10, 16, 24}", "claimed in Blok's g = 2 report, certified in 2026", null], [26, 88, "{16, 26, 88}", "certified in 2026 (U)", null],
  [28, 58, "{16, 28, 58}", "certified in 2026 (Y)", null], [30, 56, "{16, 30, 56}", "certified in 2026 (Z)", null],
  [34, 20, "{16, 20, 34}", "the same position as after 20 and 34", null], [36, 23, "{16, 23, 36}", "finite: 1,179,780 positions", null],
];
function lessonAnswer(root) {
  let i = 0, score = 0, seen = 0;
  const q = el("div", { class: "story" }), opts = el("div", { class: "row" }), msg = el("p", { class: "msg", "aria-live": "polite" });
  const after = el("div", { class: "row" });
  function legalAfter(r, x) {
    for (let k = 0; k * r <= x; k++) if ((x - k * r) % 16 === 0) return false;   // x is paid by 16s and rs
    return true;
  }
  function ask() {
    const [r, ans] = TABLE[i];
    q.innerHTML = `<p>You opened with <b>16</b>. The computer replies <b>${r}</b>. Which answer leaves a losing position for it?</p>`;
    const pool = new Set([ans]);
    const cands = [3, 5, 7, 9, 10, 11, 12, 13, 14, 15, 17, 19, 20, 21, 23, 25, 34, 40, 56, 58, 88].filter((x) => legalAfter(r, x) && x !== ans);
    let k = (r * 7) % cands.length;
    while (pool.size < 4) { pool.add(cands[k % cands.length]); k += 5; }
    const list = [...pool].sort((x, y) => x - y);
    opts.replaceChildren(...list.map((x) => el("button", { class: "tile", type: "button", onclick: () => answer(x) }, x)));
    msg.className = "msg"; msg.textContent = ""; after.replaceChildren();
  }
  function answer(x) {
    const [r, ans, dest, why, finite] = TABLE[i];
    seen++;
    opts.querySelectorAll("button").forEach((b) => { b.disabled = true; if (Number(b.textContent) === ans) b.classList.add("good"); else if (Number(b.textContent) === x) b.classList.add("bad"); });
    if (x === ans) { score++; msg.className = "msg win"; msg.innerHTML = `Yes: ${r} is answered by ${ans}, reaching ${dest} (${why}).`; }
    else { msg.className = "msg lose"; msg.innerHTML = `The certified answer is ${ans}, reaching ${dest} (${why}). Your choice ${x} is not the one this table certifies.`; }
    if (finite) after.append(el("button", { class: "ctrl", type: "button", onclick: (e) => {
      const s = new Engine(finite), w = s.winningMove(s.initialState);
      e.currentTarget.replaceWith(el("span", { class: "note" }, w === 0 ? `Checked here: ${dest} is a losing position for the player to move (${plural(s.memo.size, "position")} examined).` : `Unexpected: ${dest} has the winning move ${w}.`));
    } }, `Check ${dest} yourself`));
    after.append(el("button", { class: "ctrl primary", type: "button", onclick: () => {
      i = (i + 1) % TABLE.length;
      if (i === 0) { msg.className = "msg win"; msg.textContent = `All 16 replies done: ${score} of ${seen} answered on the first try.`; markDone("answer"); }
      ask();
    } }, i === TABLE.length - 1 ? "Finish" : "Next reply"));
  }
  root.append(
    el("p", { class: "eyebrow" }, "LESSON 5 · THE OPENING 16, 1982–2026"),
    el("h2", {}, "Answer the reply"),
    story("Nobody knows who wins after the opening 16. One way to show the opener wins is to answer every reply. A reply r <b>loses</b> when the opener has an answer a that leaves {16, r, a} as a losing position.",
          "Odd replies lose by Hutchings' theorem. The even replies up to 36 now all have certified answers. Find them."),
    el("div", { class: "game" }, q, opts, msg, after),
  );
  ask();
}

// ---------------------------------------------------------------- lesson 6: assay a certificate
function lessonAssay(root) {
  // E = {8,14}: half {4,7}, t = 17. Even obligations 2g for the gaps g; odd obligations the odd gaps above 1.
  const half = [4, 7], t = 17, pay = paidUpTo(half, t), gaps = [];
  for (let n = 1; n <= t; n++) if (!pay[n]) gaps.push(n);
  const evenReplies = { 2: [3, null], 4: [6, "C = {4, 6}"], 6: [4, "C = {4, 6}"], 10: [19, null], 12: [10, "{8, 10, 12, 14}, Blok's pairing family"],
                        18: [25, null], 20: [9, null], 26: [17, null], 34: [27, null] };
  const obligations = [...gaps.map((g) => 2 * g), ...gaps.filter((g) => g > 1 && g % 2)].sort((a, b) => a - b);
  const tbody = el("tbody"), msg = el("p", { class: "msg", "aria-live": "polite" });
  const rows = obligations.map((m) => {
    const node = m % 2 === 0 ? evenReplies[m] : null;
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
    el("p", { class: "eyebrow" }, "LESSON 6 · HOW 2026 CERTIFICATES WORK"),
    el("h2", {}, "Assay a certificate"),
    story("To prove a short position is losing, you list its <b>obligations</b>, the only moves the Quiet End Theorem leaves open, and answer each one with a reply that reaches a known losing position.",
          "{8, 14} is the double of the quiet ender {4, 7}. It has 14 obligations. The computer below finds or checks each reply. In the 2026 campaign the same kind of check ran on positions with hundreds of millions of states, twice, by two independent programs."),
    el("div", { class: "game" }, el("div", { class: "row" }, el("button", { class: "ctrl primary", type: "button", onclick: (e) => { e.currentTarget.disabled = true; assay(); } }, "Assay all 14")),
       el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ...["move", "kind", "reply", "reaches", "check"].map((h) => el("th", {}, h)))), tbody)), msg),
  );
}

// ---------------------------------------------------------------- lesson 7: the frontier
// Every obligation of {16, 38}: k is the kind of move, s its status as of October 10, 2026.
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
  {"m": 42, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 44, "k": "short", "s": "certified", "why": "{16,38,44} moves by 24 to B24={16,24,38,44}, a certified losing position"},
  {"m": 45, "k": "odd", "s": "search", "why": "{16,38,45} has a winning reply (the ledger's scan)"},
  {"m": 46, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 47, "k": "odd", "s": "search", "why": "{16,38,47} has a winning reply (the ledger's scan)"},
  {"m": 49, "k": "odd", "s": "search", "why": "{16,38,49} has a winning reply (the ledger's scan)"},
  {"m": 50, "k": "long", "s": "search", "why": "{16,38,50} is won by 79 (search)"},
  {"m": 52, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 53, "k": "odd", "s": "search", "why": "{16,38,53} has a winning reply (the ledger's scan)"},
  {"m": 55, "k": "odd", "s": "search", "why": "{16,38,55} has a winning reply (the ledger's scan)"},
  {"m": 56, "k": "short", "s": "certified", "why": "{16,38,56} moves by 60 to B56={16,38,56,60}, a certified losing position"},
  {"m": 58, "k": "long", "s": "search", "why": "{16,38,58} is won by 11 (search)"},
  {"m": 60, "k": "short", "s": "search", "why": "{16,38,60} is won by the odd move 17 (search)"},
  {"m": 61, "k": "odd", "s": "search", "why": "{16,38,61} has a winning reply (the ledger's scan)"},
  {"m": 62, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 63, "k": "odd", "s": "search", "why": "{16,38,63} has a winning reply (the ledger's scan)"},
  {"m": 66, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 68, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 69, "k": "odd", "s": "search", "why": "{16,38,69} is won by 25 (search)"},
  {"m": 71, "k": "odd", "s": "search", "why": "{16,38,71} is won by 73 (search)"},
  {"m": 72, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its hard long children have no witness yet"},
  {"m": 74, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 77, "k": "odd", "s": "search", "why": "{16,38,77} is won by 27 (search)"},
  {"m": 78, "k": "long", "s": "search", "why": "{16,38,78} is won by 27 (search)"},
  {"m": 79, "k": "odd", "s": "search", "why": "{16,38,79} is won by 50 (search)"},
  {"m": 82, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 84, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 85, "k": "odd", "s": "search", "why": "{16,38,85} is won by 105 (search)"},
  {"m": 87, "k": "odd", "s": "search", "why": "{16,38,87} is won by 273 (search)"},
  {"m": 88, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its hard long children have no witness yet"},
  {"m": 90, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 93, "k": "odd", "s": "search", "why": "{16,38,93} is won by 83 (search)"},
  {"m": 94, "k": "long", "s": "search", "why": "{16,38,94} is won by 43 (search)"},
  {"m": 98, "k": "long", "s": "search", "why": "{16,38,98} is won by 31 (search)"},
  {"m": 100, "k": "long", "s": "search", "why": "{16,38,100} is won by 41 (search)"},
  {"m": 101, "k": "odd", "s": "search", "why": "{16,38,101} is won by 33 (search)"},
  {"m": 104, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its hard long children have no witness yet"},
  {"m": 106, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 109, "k": "odd", "s": "open", "why": "not settled yet"},
  {"m": 110, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 116, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 117, "k": "odd", "s": "open", "why": "not settled yet"},
  {"m": 120, "k": "short", "s": "ladder", "why": "a rung of the ladder 56, 72, 88, 104, 120, 136; its hard long children have no witness yet"},
  {"m": 122, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 125, "k": "odd", "s": "open", "why": "not settled yet"},
  {"m": 126, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 132, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 136, "k": "short", "s": "search", "why": "{16,38,136} is won by the odd move 37 (search)"},
  {"m": 138, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 142, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 148, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 154, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 158, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 164, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 170, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 174, "k": "long", "s": "search", "why": "{16,38,174} is won by 45 (search)"},
  {"m": 180, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 186, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 196, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 202, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 212, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 218, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 234, "k": "long", "s": "open", "why": "not settled yet"},
  {"m": 250, "k": "long", "s": "open", "why": "not settled yet"},
];
function lessonFrontier(root) {
  const detail = el("p", { class: "detail", "aria-live": "polite" }, "Click a tile to see what is known about it.");
  const groups = [["odd", "Odd answers"], ["short", "Even answers that leave a short position"], ["long", "Even answers that leave a long position"]];
  const box = el("div", { class: "game" });
  const cls = { certified: "bad", search: "paid", open: "", ladder: "gold" };
  for (const [k, title] of groups) {
    const tiles = el("div", { class: "tiles" });
    FRONTIER.filter((r) => r.k === k).forEach((r) => tiles.append(el("button", { class: "tile sm " + cls[r.s], type: "button",
      onclick: () => { detail.innerHTML = `<b>${r.m}</b>: ${r.why}.`; } }, r.m)));
    box.append(el("p", { class: "note" }, title), tiles);
  }
  const counts = (s) => FRONTIER.filter((r) => r.s === s).length;
  box.append(el("div", { class: "legend" },
    el("span", {}, el("i", { style: "border-color: var(--oxide); background: var(--oxide-soft)" }), `ruled out, certified (${counts("certified")})`),
    el("span", {}, el("i", { style: "border-color: transparent; background: var(--paid)" }), `ruled out by search (${counts("search")})`),
    el("span", {}, el("i", { style: "border-color: var(--gilt); background: var(--gilt-soft)" }), `ladder rungs (${counts("ladder")})`),
    el("span", {}, el("i", { style: "border-color: var(--copper); background: var(--copper-soft)" }), `open (${counts("open")})`)), detail);
  root.append(
    el("p", { class: "eyebrow" }, "LESSON 7 · OCTOBER 2026"),
    el("h2", {}, "The frontier: the reply 38"),
    story("Every even reply to 16 up to 36 has an answer. The reply 38 does not, yet. Because {16, 38} is short, any answer must be one of these 98 moves.",
          "Eleven are ruled out by certified losing positions. Search has ruled out most others. The short candidates 72, 88, 104 and 120 form a <b>ladder</b> with 56 and 136: each rung leads back to the rungs below it, so at most one can be the answer."),
    box,
    el("p", { class: "note" }, "Status as of October 10, 2026, from the campaign records at github.com/rudi-cilibrasi/sylver-coinage. Search results are discovery output, not certificates."),
  );
}

// ---------------------------------------------------------------- navigation
const LESSONS = [
  ["play", "Mint and lose", "Conway's game", lessonPlay],
  ["sylvester", "The largest unpayable amount", "Sylvester, 1884", lessonSylvester],
  ["enders", "Steal a strategy", "Hutchings, 1982", lessonEnders],
  ["quiet", "Quiet ends, short and long", "Winning Ways", lessonQuiet],
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
  try { history.replaceState(null, "", "#" + LESSONS[i][0]); } catch (e) { /* not allowed here */ }
  if (focus) main.focus({ preventScroll: false });
}
const lessonFromHash = () => LESSONS.findIndex(([id]) => "#" + id === location.hash);

if (typeof module !== "undefined") {
  module.exports = { FRONTIER, LESSONS, TABLE, isPaid, minimal, paidUpTo };
} else {
  window.addEventListener("hashchange", () => { const i = lessonFromHash(); if (i >= 0 && i !== current) show(i, false); });
  show(Math.max(0, lessonFromHash()), false);
}
