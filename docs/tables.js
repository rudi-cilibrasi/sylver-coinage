// Auto-generated Blok-style cross tables from the campaign's audited
// artifacts.  A table for base B has extension sets along its first row
// and column; each interior cell reports the campaign's knowledge of
// B ∪ row ∪ column: "[]"  proved P, "[w]" proved N with recorded winning
// reply w, "N" proved N (winner unrecorded), "·" unknown.
// Pure functions; usable from the page and from node (for tests).
"use strict";

function tgcd(a, b) { while (b) { [a, b] = [b, a % b]; } return a; }

function canRepresentT(gens, value) {
  const reachable = new Array(value + 1).fill(false);
  reachable[0] = true;
  for (let v = 1; v <= value; ++v)
    for (const g of gens)
      if (v >= g && reachable[v - g]) { reachable[v] = true; break; }
  return reachable[value];
}

function minimalGeneratorsT(gens) {
  const sorted = [...new Set(gens)].sort((a, b) => a - b);
  return sorted.filter((g) =>
    !canRepresentT(sorted.filter((x) => x !== g), g));
}

function keyOf(gens) { return minimalGeneratorsT(gens).join(","); }

// ---- data ingestion -----------------------------------------------------

function parseCache(text) {
  const outcomes = new Map();
  for (const line of text.split("\n")) {
    const cut = line.lastIndexOf(" ");
    if (cut < 0) continue;
    outcomes.set(line.slice(0, cut), line.slice(cut + 1) === "1");
  }
  return outcomes;
}

// Winner sources: JSONL ledgers ({pos|base, rows|move...}) and RUN-format
// text scans ("move=M N winning_move=W ..." rows for a fixed base).
function parseWinners(sources) {
  const winners = new Map();          // key -> winning reply
  const add = (baseGens, move, winner) => {
    if (winner === null || winner === undefined) return;
    winners.set(keyOf([...baseGens, move]), winner);
  };
  // A scanned reply that reaches a P-position is itself a winning reply
  // to the scan's base — record both directions of every row.
  const addP = (baseGens, move) => winners.set(keyOf(baseGens), move);
  for (const { kind, base, text } of sources) {
    if (kind === "jsonl-wave") {
      for (const line of text.split("\n")) {
        if (!line.trim()) continue;
        const entry = JSON.parse(line);
        for (const [move, outcome, winner] of entry.rows) {
          if (outcome === "N") add(entry.pos, move, winner);
          else addP(entry.pos, move);
        }
      }
    } else if (kind === "jsonl-rows") {
      for (const line of text.split("\n")) {
        if (!line.trim()) continue;
        const entry = JSON.parse(line);
        if (entry.outcome === "N") add(entry.base, entry.move, entry.winning_move);
        else addP(entry.base, entry.move);
      }
    } else if (kind === "run-text") {
      for (const line of text.split("\n")) {
        const nrow = /^move=(\d+) N winning_move=(\d+)/.exec(line.trim());
        if (nrow) { add(base, parseInt(nrow[1], 10), parseInt(nrow[2], 10)); continue; }
        const prow = /^move=(\d+) P /.exec(line.trim());
        if (prow) addP(base, parseInt(prow[1], 10));
      }
    }
  }
  return winners;
}

// ---- certified knowledge outside the cache ------------------------------
// The certified P-node graph lives in code (sylver/short_certificates.py),
// not in the outcome cache.  This curated block mirrors its NODES and
// SHORT_NATIVE_FINITE_P_POSITIONS tables plus the certified opening-16 and
// pair-edge replies; provenance for every entry is that file and the
// RUN_*.txt records.
const CERTIFIED_P = [
  [2, 3], [4, 6], [8, 14], [12, 14, 16], [12, 16, 22], [8, 12],
  [12, 16, 20, 22, 26], [8, 10, 22], [10, 16, 24], [16, 20, 34],
  [14, 16, 20, 26], [16, 20, 30, 34, 44], [8, 20, 26], [8, 20, 30],
  [16, 20, 26, 28, 38], [16, 20, 22, 28, 34], [16, 20, 28, 30, 42],
  [16, 20, 28, 38, 50], [16, 26, 36, 56],
  [16, 20, 34, 58, 291], [16, 26, 30, 36, 99], [16, 26, 36, 44, 56, 57],
  [16, 26, 36, 46, 56, 153], [16, 26, 36, 50, 56, 109],
  [16, 26, 36, 54, 56, 83], [16, 26, 36, 53, 56, 66],
  [16, 26, 36, 37, 56, 70], [16, 26, 36, 56, 76, 131],
  [16, 26, 36, 55, 56, 86], [16, 26, 36, 56, 102, 201],
];
const CERTIFIED_WINNERS = [
  [[16, 2], 3], [[16, 4], 6], [[16, 6], 7], [[16, 8], 14], [[16, 10], 9],
  [[16, 12], 14], [[16, 14], 8], [[16, 18], 5], [[16, 20], 34],
  [[16, 22], 12], [[16, 24], 10],
  [[16, 26, 36], 56], [[16, 26, 56], 36],
];

function applyCertified(cache, winners) {
  for (const gens of CERTIFIED_P) {
    const key = keyOf(gens);
    if (!cache.has(key)) cache.set(key, true);
  }
  for (const [gens, winner] of CERTIFIED_WINNERS) {
    const key = keyOf(gens);
    if (!winners.has(key)) winners.set(key, winner);
  }
}

// ---- table construction -------------------------------------------------

function subsetsOfBase(cache, baseGens) {
  // Every cached position whose generators contain the base's minimal
  // generators; returns [{extra: [...], key, isP}] with |extra| <= 2.
  const baseMin = minimalGeneratorsT(baseGens);
  const results = [];
  for (const [key, isP] of cache) {
    const gens = key.split(",").map(Number);
    if (baseMin.some((b) => !gens.includes(b))) continue;
    const extra = gens.filter((g) => !baseMin.includes(g));
    if (extra.length <= 2) results.push({ extra, key, isP });
  }
  return results;
}

function buildCrossTable(cache, winners, baseGens, maxAxis = 48,
                         probeLimit = 600) {
  const baseMin = minimalGeneratorsT(baseGens);
  const baseKey = baseMin.join(",");
  const entries = subsetsOfBase(cache, baseGens);
  const rowValues = new Set();
  const colValues = new Set();
  for (const { extra } of entries) {
    if (extra.length === 1) { rowValues.add(extra[0]); colValues.add(extra[0]); }
    if (extra.length === 2) { rowValues.add(extra[0]); colValues.add(extra[1]); }
  }
  // Most single replies reduce by absorption (the reply generates part of
  // the base), so their cache keys are not supersets of the base; probe
  // them directly and let the cell lookup follow the exact reduction.
  for (let m = 2; m <= probeLimit; ++m) {
    const key = keyOf([...baseMin, m]);
    if (key === baseKey) continue;               // m is generated: illegal
    if (cache.has(key) || winners.has(key)) {
      rowValues.add(m);
      colValues.add(m);
    }
  }
  const rows = [...rowValues].sort((a, b) => a - b);
  const cols = [...colValues].sort((a, b) => a - b);
  const truncated = { rows: Math.max(0, rows.length - maxAxis),
                      cols: Math.max(0, cols.length - maxAxis) };
  const cell = (gens) => {
    const key = keyOf(gens);
    // A cell whose extras are absorbed into a smaller position is shown
    // for what it reduces to; the reduction is exact semigroup identity.
    // A recorded winning reply itself proves N (its destination is P),
    // which covers scan bases that never received their own cache row.
    if (cache.has(key) && cache.get(key)) return "[]";
    if (winners.has(key)) return "[" + winners.get(key) + "]";
    if (cache.has(key)) return "N";
    return "·";
  };
  const matrix = [];
  const useRows = [null, ...rows.slice(0, maxAxis)];   // null = empty set
  const useCols = [null, ...cols.slice(0, maxAxis)];
  for (const r of useRows) {
    const line = [];
    for (const c of useCols) {
      if (r !== null && c !== null && c <= r) { line.push(""); continue; }
      const gens = [...baseMin];
      if (r !== null) gens.push(r);
      if (c !== null && c !== r) gens.push(c);
      line.push(cell(gens));
    }
    matrix.push(line);
  }
  return { baseKey, rows: useRows, cols: useCols, matrix, truncated,
           entries: entries.length };
}

if (typeof module !== "undefined") {
  module.exports = { parseCache, parseWinners, buildCrossTable,
                     applyCertified, minimalGeneratorsT, keyOf };
}
