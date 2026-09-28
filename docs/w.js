// Row descriptions for the obligation pages (w.html, u.html), from a campaign
// audit (sylver/campaigns/*/audit.json). Kept separate from the pages so the
// node tests can check every obligation is described.
"use strict";

const EVIDENCE_LABELS = {
  "book": "Book certificate",
  "finite-witness": "finite witness",
  "certified-node": "certified infinite P-position",
  "w-is-p": "W is P",
  "open": "open",
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
  } else if (row.evidence === "w-is-p") {
    out.answer = "reply " + row.reply + " → W={" + row.destination + "}";
    out.title = "W is P: its own audit covers all 52 of its obligations";
    out.link = row.certificate;
  } else {
    out.answer = "unrecognized evidence";
  }
  return out;
}

// An obligation the audit leaves open, with what is known about it.
function describeOpen(move, row) {
  const counts = Object.entries(row.odd_replies_classified || {}).map(([k, n]) => n + " " + k).join(", ");
  const name = row.position.split("=")[0];
  return {
    move: Number(move), position: "{" + row.destination_of_move + "}", evidence: "open",
    answer: name + ((row.P_replies || []).length
      ? ": P replies found: " + row.P_replies.join(", ")
      : row.first_unclassified_odd_reply ? ": every odd reply below " + row.first_unclassified_odd_reply + " is N"
      : " is open"),
    title: row.position + " — " + counts, states: null, link: null, checkable: false,
  };
}

// All rows in move order, with per-evidence counts and the audit's verdict.
function describeAudit(audit) {
  const rows = Object.entries(audit.obligations)
    .map(([move, row]) => describeObligation(move, row))
    .concat(Object.entries(audit.open || {}).map(([move, row]) => describeOpen(move, row)))
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
  module.exports = { checkLabel, describeAudit, describeObligation, describeOpen };
}
