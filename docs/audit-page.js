// Shared page logic for the obligation pages (w.html, u.html): load a campaign
// audit, render one row per obligation, and offer in-browser checks of the
// smaller Book certificates with book.js and solver.js.
"use strict";

const LOCAL = new URLSearchParams(location.search).has("local");   // serve the checkout: /docs/w.html?local
const RAW = LOCAL ? "../" : "https://raw.githubusercontent.com/rudi-cilibrasi/sylver-coinage/main/";
const BLOB = "https://github.com/rudi-cilibrasi/sylver-coinage/blob/main/";
const BROWSER_LIMIT = 140;   // largest leaf Frobenius number the page will replay

function solveInBrowser(gens) {
  return new SylverSolver(gens, 6000000).solve().winningMove === null ? "P" : "N";
}

function cell(tr, cls, content) {
  const td = document.createElement("td");
  td.className = cls;
  if (content instanceof Node) td.appendChild(content); else td.textContent = content;
  tr.appendChild(td);
  return td;
}

async function addCheck(check, r) {
  try {
    const proof = await (await fetch(RAW + r.link)).json();
    const leaf = largestLeaf(proof);
    if (leaf > BROWSER_LIMIT) {
      check.className = "muted"; check.textContent = "leaf too large (F=" + leaf + ")";
      return;
    }
    const button = document.createElement("button");
    button.textContent = "Check";
    button.addEventListener("click", () => {
      button.disabled = true; button.textContent = "checking…";
      setTimeout(() => {
        const label = checkLabel(checkCertificate(proof, solveInBrowser));
        const span = document.createElement("span");
        span.className = label.cls; span.textContent = label.text;
        check.textContent = ""; check.appendChild(span);
      }, 20);
    });
    check.className = ""; check.textContent = ""; check.appendChild(button);
  } catch (e) {
    check.className = "muted"; check.textContent = "could not load the certificate";
  }
}

// options: campaign (directory under sylver/campaigns), table and status
// element ids, verdict(described) -> {ok, text} for the status line, and an
// optional section (a key of a nested audit, such as "Z" in the Z record).
async function renderAuditPage(options) {
  const status = document.getElementById(options.status);
  const path = "sylver/campaigns/" + options.campaign + "/audit.json";
  let described;
  try {
    const audit = await (await fetch(RAW + path)).json();
    described = describeAudit(options.section ? audit[options.section] : audit);
  } catch (e) {
    status.textContent = "Could not load the audit: " + e.message + ". The page reads " + path +
      " from GitHub; try again later.";
    return;
  }
  const body = document.querySelector("#" + options.table + " tbody");
  const pending = [];
  for (const r of described.rows) {
    const tr = document.createElement("tr");
    if (r.evidence === "open") tr.className = "open";
    cell(tr, "num", String(r.move));
    cell(tr, "pos", r.position);
    cell(tr, "", r.evidence);
    const answer = r.link ? document.createElement("a") : document.createElement("span");
    if (r.link) answer.href = BLOB + r.link;
    answer.textContent = r.answer;
    if (r.title) answer.title = r.title;
    cell(tr, "", answer);
    cell(tr, "num", r.states === null ? "" : r.states.toLocaleString("en-US"));
    const check = cell(tr, "muted", "");
    if (r.checkable) {
      check.textContent = "loading…";
      pending.push(addCheck(check, r));
    } else {
      check.textContent = r.evidence === "finite witness" ? "native + Python"
        : r.evidence === "finite witness (native + Kunz)" ? "native + Kunz"
        : r.evidence === "open" ? "" : "repository";
    }
    body.appendChild(tr);
  }
  document.getElementById(options.table).hidden = false;
  const verdict = options.verdict(described);
  status.textContent = verdict.text;
  if (!verdict.ok) status.className = "bad";
  await Promise.all(pending);
}
