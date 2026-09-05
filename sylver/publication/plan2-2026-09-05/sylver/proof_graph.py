"""Evidence-based Sylver routing and finite proof obligations.

This graph inherits explicitly identified exact/cache/theorem leaves. It does
not turn source claims, scan limits, or cycles of proposed replies into facts.
All new N edges are legal one-move semigroup identities; new P nodes require
complete move coverage and (for short gcd-two nodes) the Quiet End Theorem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from math import gcd
from pathlib import Path

from sylver.short_certificates import NODES, OPENING_16_EVEN_RESPONSES, minimal_generators
from sylver.solver import FiniteSolver
from sylver.x_even_flank import known_p_semigroups


def key(position):
    return ",".join(map(str, minimal_generators(position)))


def position(key_string):
    return tuple(map(int, key_string.split(",")))


@lru_cache(maxsize=32768)
def membership(generators, bound):
    """Exact membership through bound, including for infinite-gap monoids."""
    mask = (1 << (bound + 1)) - 1
    bits = 1
    for generator in generators:
        shift = generator
        while shift <= bound:
            bits |= (bits << shift) & mask
            shift *= 2
    return bits


@lru_cache(maxsize=None)
def profile(generators):
    divisor = gcd(*generators)
    result = {"gcd": divisor, "complete_moves": False, "moves": []}
    if divisor == 1:
        solver = FiniteSolver(generators)
        result.update(frobenius=solver.frobenius, complete_moves=True,
                      moves=[m for m in solver.gaps() if m > 1],
                      tail="finite")
    elif divisor == 2 and generators != (2,):
        half = FiniteSolver(tuple(g // 2 for g in generators))
        quiet = half.is_quiet_ender()
        even = [2 * m for m in half.gaps()]
        odd = [m for m in half.gaps() if m > 1 and m % 2] if quiet else []
        result.update(half_frobenius=half.frobenius, quiet=quiet,
                      even_moves=even, exceptional_odds=odd,
                      complete_moves=quiet, moves=sorted(even + odd),
                      tail="quiet-end-theorem" if quiet else "unresolved-odd-tail")
    else:
        result["tail"] = "unresolved-gcd-family"
    return result


class ProofGraph:
    def __init__(self):
        self.facts = {}  # key -> outcome and evidence (only established results)
        self.sources = {}
        self.nodes = {}  # inspected nodes and unresolved obligations
        self.p_index = []
        self.p_keys = []
        self.index_bound = 3
        self.index_version = 0
        self.p_version = 0
        self.route_misses = {}

    def add_fact(self, generators, outcome, evidence):
        k = key(generators)
        previous = self.facts.get(k)
        if previous is not None:
            if previous["outcome"] != outcome:
                raise ValueError(f"conflicting evidence for {k}")
            return False
        if outcome not in ("P", "N"):
            raise ValueError("only established P/N results are facts")
        self.facts[k] = {"outcome": outcome, "evidence": evidence}
        if outcome == "P":
            self.p_keys.append(k)
            self.p_version += 1
        return True

    def load_exact_cache(self, path):
        source = str(path.resolve())
        # Read a stable byte snapshot even if the campaign atomically replaces
        # the source while this process is working.
        data = path.read_bytes()
        self.sources[source] = {"sha256": hashlib.sha256(data).hexdigest(),
                                "kind": "inherited-exact-cache"}
        count = 0
        for line in data.decode().splitlines():
            k, value = line.split()
            if value not in ("0", "1"):
                raise ValueError(f"invalid cache value: {line}")
            # Existing campaign caches are canonical. Canonicalization is
            # checked for P-index entries and every queried position below.
            fact = {"outcome": "P" if value == "1" else "N",
                    "evidence": {"kind": "exact-cache", "source": source}}
            previous = self.facts.get(k)
            if previous and previous["outcome"] != fact["outcome"]:
                raise ValueError(f"cache conflict: {k}")
            if previous is None:
                self.facts[k] = fact
                count += 1
                if value == "1":
                    self.p_keys.append(k)
                    self.p_version += 1
        return count

    def seed_repository(self):
        for generators, source in known_p_semigroups().items():
            self.add_fact(generators, "P", {"kind": "repository-certificate",
                                           "source": source})
        # The unbounded pairing proof was added after the original node table.
        self.add_fact((8, 12), "P", {"kind": "pairing-theorem",
                                    "source": "sylver/eight_twelve.py"})
        for node in NODES:
            for move, reply, _ in node.even_responses:
                self.add_fact((*node.generators, move, reply), "P",
                              {"kind": "repository-certificate-edge",
                               "source": f"node:{node.name}",
                               "move": move, "reply": reply})
        for move, reply, _ in OPENING_16_EVEN_RESPONSES:
            self.add_fact((16, move, reply), "P",
                          {"kind": "repository-opening-certificate",
                           "move": move, "reply": reply})

    def _index(self):
        if self.index_version == self.p_version:
            return
        entries = []
        for k in self.p_keys[self.index_version:]:
            gs = position(k)
            if key(gs) != k:
                raise ValueError(f"noncanonical P-cache entry: {k}")
            entries.append((gs, k))
        bound = max(self.index_bound, max((max(gs) for gs, _ in entries), default=3))
        if bound > self.index_bound:
            self.p_index = [(gs, k, bits, membership(gs, bound))
                            for gs, k, bits, _ in self.p_index]
        self.index_bound = bound
        # Append in discovery order: a previous miss need only consider the
        # new suffix. Existing P facts never change in this monotone graph.
        self.p_index.extend((gs, k, sum(1 << g for g in gs), membership(gs, bound))
                            for gs, k in entries)
        self.index_version = self.p_version

    def route(self, generators):
        """Find any known P-destination reachable in one legal move.

        S+r=Q iff S is contained in Q and Q's minimal generators absent
        from S consist of exactly r. This has no numerical reply cutoff.
        """
        gs = minimal_generators(generators)
        k = key(gs)
        if k in self.facts:
            return self.facts[k]
        if gcd(*gs) == 1:
            finite = FiniteSolver(gs)
            if finite.frobenius > 1 and finite.is_quiet_ender():
                self.add_fact(gs, "N", {"kind": "quiet-ender-theorem",
                                        "frobenius": finite.frobenius})
                return self.facts[k]
        if self.route_misses.get(k) == self.p_version:
            return None
        self._index()
        bound = max(self.index_bound, max(gs))
        sbits = membership(gs, bound)
        sgens = sum(1 << g for g in gs)
        for q, qkey, qgens, qbits in self.p_index[self.route_misses.get(k, 0):]:
            if bound > self.index_bound:
                qbits = membership(q, bound)
            if sgens & ~qbits:
                continue
            missing = qgens & ~sbits
            if missing.bit_count() != 1:
                continue
            move = missing.bit_length() - 1
            if move <= 1 or minimal_generators((*gs, move)) != q:
                raise AssertionError("invalid indexed route")
            self.add_fact(gs, "N", {"kind": "winning-edge", "move": move,
                                    "destination": qkey})
            return self.facts[k]
        self.route_misses[k] = self.p_version
        return None

    def inspect(self, generators):
        gs = minimal_generators(generators)
        k = key(gs)
        fact = self.route(gs)
        if fact:
            self.nodes[k] = {"position": list(gs), **fact}
            return self.nodes[k]
        info = profile(gs)
        obligations = []
        for move in info["moves"]:
            child = minimal_generators((*gs, move))
            ck = key(child)
            outcome = self.route(child)
            obligations.append({"move": move, "destination": ck,
                                "outcome": outcome["outcome"] if outcome else "unknown"})
            if outcome and outcome["outcome"] == "P":
                self.add_fact(gs, "N", {"kind": "winning-edge", "move": move,
                                        "destination": ck})
                break
        if k not in self.facts and info["complete_moves"] and all(
                row["outcome"] == "N" for row in obligations):
            self.add_fact(gs, "P", {"kind": "complete-cover",
                                    "tail": info["tail"],
                                    "obligations": obligations})
        fact = self.facts.get(k, {"outcome": "unknown"})
        self.nodes[k] = {"position": list(gs), **fact, "profile": info,
                         "obligations": obligations,
                         "open_moves": [r["move"] for r in obligations
                                        if r["outcome"] == "unknown"]}
        return self.nodes[k]

    def close(self, targets):
        """Monotone propagation: only already-founded facts support new ones."""
        targets = sorted(set(map(tuple, targets)), key=lambda p: (len(p), p), reverse=True)
        while True:
            before = len(self.facts)
            for gs in targets:
                self.inspect(gs)
            if len(self.facts) == before:
                break
        return [self.nodes[key(gs)] for gs in targets]

    def export(self, path, extra=None):
        # Preserve every discovery outside the inherited caches, even when
        # a focused pass did not inspect the node that first used it. The
        # large input caches remain fingerprinted rather than duplicated.
        support = {}
        todo = [*self.nodes, *(k for k, fact in self.facts.items()
                              if fact["evidence"]["kind"] != "exact-cache")]
        for node in self.nodes.values():
            todo.extend(row["destination"] for row in node.get("obligations", []))
        while todo:
            k = todo.pop()
            if k in support or k not in self.facts:
                continue
            support[k] = self.facts[k]
            ev = support[k]["evidence"]
            if ev["kind"] == "winning-edge":
                todo.append(ev["destination"])
            elif ev["kind"] == "complete-cover":
                todo.extend(r["destination"] for r in ev["obligations"])
        result = {"schema": 1, "sources": self.sources, "nodes": self.nodes,
                  "support": support, **(extra or {})}
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", action="append", type=Path, required=True)
    parser.add_argument("--targets", type=Path, help="JSON list of generator lists")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    graph = ProofGraph()
    for path in args.cache:
        graph.load_exact_cache(path)
    graph.seed_repository()
    targets = json.loads(args.targets.read_text()) if args.targets else [(16, 26)]
    graph.close(targets)
    graph.export(args.output)


if __name__ == "__main__":
    main()
