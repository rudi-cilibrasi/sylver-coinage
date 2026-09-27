// Row descriptions for the W page (w.html), from the campaign audit
// (sylver/campaigns/w-p-2026-09-27/audit.json). Kept separate from the page
// so the node test can check every obligation is described.
"use strict";

const EVIDENCE_LABELS = {
  "book": "Book certificate",
  "finite-witness": "finite witness",
  "certified-node": "certified infinite P-position",
};

// One table row for obligation `move` with audit entry `row`.
function describeObligation(move, row) {
  const out = {
    move: Number(move),
    position: "{" + row.destination_of_move + "}",
    evidence: EVIDENCE_LABELS[row.evidence] || row.evidence,
    answer: "",
    title: null,
    states: null,
    link: null,
    checkable: row.evidence === "book",
  };
  if (row.evidence === "book") {
    out.answer = "certificate, C=" + row.C;
    out.states = row.states;
    out.link = row.certificate;
  } else if (row.evidence === "finite-witness") {
    out.answer = "reply " + row.reply + ": replay receipt";
    out.title = "{" + row.destination + "} is P";
    out.states = row.states;
    out.link = row.receipt;
  } else if (row.evidence === "certified-node") {
    out.answer = "reply " + row.reply + " → {" + row.destination + "}";
    out.title = "{" + row.destination + "} is P: " + row.certificate;
    out.link = row.source;
  } else {
    out.answer = "unrecognized evidence";
  }
  return out;
}

// All rows in move order, with per-evidence counts and the audit's verdict.
function describeAudit(audit) {
  const rows = Object.entries(audit.obligations)
    .map(([move, row]) => describeObligation(move, row))
    .sort((a, b) => a.move - b.move);
  const counts = {};
  for (const r of rows) counts[r.evidence] = (counts[r.evidence] || 0) + 1;
  return { rows, counts, outcome: audit.outcome, total: audit.summary.obligations, failures: audit.failures || [] };
}

// How a Check result reads on the page: a solver that ran out of its state
// budget has not rejected anything.
function checkLabel(result) {
  if (result.valid && result.outcome === "N") return { cls: "ok", text: "valid: N" };
  if (result.error && result.error.includes("state limit")) return { cls: "muted", text: "too large for the browser" };
  return { cls: "bad", text: "rejected: " + (result.error || "outcome differs") };
}

if (typeof module !== "undefined") {
  module.exports = { checkLabel, describeAudit, describeObligation };
}
