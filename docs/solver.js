// Exact finite Sylver Coinage evaluator — a JavaScript port of the
// repository's Python reference (sylver/solver.py): the same bitset
// recurrence, the same commutative reply-pairing optimization.  Bit n of
// a BigInt state is set exactly when n is in the numerical semigroup.
"use strict";

function gcd(a, b) { while (b) { [a, b] = [b, a % b]; } return a; }

function normalize(generators) {
  const gens = [...new Set(generators)].sort((x, y) => x - y);
  if (gens.some((g) => !Number.isInteger(g) || g < 2)) {
    throw new Error("generators must be integers greater than one");
  }
  if (gens.reduce(gcd) !== 1) {
    throw new Error("exact evaluation requires generators with gcd one");
  }
  return gens;
}

function frobeniusNumber(gens) {
  // Shortest-path over residues modulo the least generator, as in the
  // native solver.  distance[r] = least representable value ≡ r (mod m).
  const m = gens[0];
  const distance = new Array(m).fill(Infinity);
  distance[0] = 0;
  const queue = [[0, 0]];
  while (queue.length) {
    queue.sort((a, b) => b[0] - a[0]);
    const [value, residue] = queue.pop();
    if (value !== distance[residue]) continue;
    for (const g of gens) {
      const candidate = value + g;
      const nr = candidate % m;
      if (candidate < distance[nr]) {
        distance[nr] = candidate;
        queue.push([candidate, nr]);
      }
    }
  }
  return Math.max(...distance) - m;
}

class SylverSolver {
  constructor(generators, stateLimit = 4000000) {
    this.gens = normalize(generators);
    this.frobenius = frobeniusNumber(this.gens);
    this.mask = (1n << BigInt(this.frobenius + 1)) - 1n;
    this.stateLimit = stateLimit;
    this.memo = new Map();
    let state = 1n;                       // zero is in every semigroup
    for (const g of this.gens) state = this.adjoin(state, g);
    this.initialState = state;
  }

  adjoin(state, move) {
    let shift = BigInt(move);
    const frob = BigInt(this.frobenius);
    let result = state;
    while (shift <= frob) {
      result |= (result << shift) & this.mask;
      shift *= 2n;
    }
    return result;
  }

  legalMoves(state) {                     // ascending, excluding 1
    const moves = [];
    for (let m = 2; m <= this.frobenius; ++m) {
      if (!((state >> BigInt(m)) & 1n)) moves.push(m);
    }
    return moves;
  }

  gaps(state) {                           // including the poisoned 1
    return [1, ...this.legalMoves(state)];
  }

  winningMove(state) {
    const key = state.toString(36);
    const found = this.memo.get(key);
    if (found !== undefined) return found;
    if (this.memo.size > this.stateLimit) {
      throw new Error("state limit exceeded — use the native solver");
    }
    let pairedLosers = 0n;
    for (const move of this.legalMoves(state)) {
      if ((pairedLosers >> BigInt(move)) & 1n) continue;
      const child = this.adjoin(state, move);
      const response = this.winningMove(child);
      if (response === 0) {
        this.memo.set(key, move);
        return move;
      }
      if (response > move) pairedLosers |= 1n << BigInt(response);
    }
    this.memo.set(key, 0);
    return 0;
  }

  solve() {
    const move = this.winningMove(this.initialState);
    return {
      generators: this.gens,
      frobenius: this.frobenius,
      winningMove: move === 0 ? null : move,
      statesEvaluated: this.memo.size,
    };
  }
}

if (typeof module !== "undefined") {
  module.exports = { SylverSolver, frobeniusNumber, normalize };
}
