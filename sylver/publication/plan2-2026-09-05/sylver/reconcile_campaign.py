"""Bounded, resumable verification and target ranking for plan option 2.

Outputs containing unpublished claims belong outside the public repository.
This command writes only its output directory, never the active siege cache.
Native timeouts remain unknown and are recorded as such.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import time
from collections import Counter, defaultdict
from math import gcd
from pathlib import Path

from sylver.parallel_solve import compile_solver
from sylver.proof_graph import ProofGraph, key, position, profile
from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import frobenius_number
from sylver.solver import FiniteSolver

NEW_PUBLIC = (16, 26, 54, 60, 62)
NATIVE_ROW = re.compile(r"([PN]) winning_move=(none|\d+) frobenius=(\d+) states=(\d+)")


class ExactChecks:
    def __init__(self, graph, output, budget, retry_timeouts=False):
        self.graph = graph
        self.output = output
        self.remaining = budget
        self.attempted = set()
        self.build = output / "build"
        self.build.mkdir(exist_ok=True)
        self.source_hash = hashlib.sha256(
            (Path(__file__).parent / "native_solver.cpp").read_bytes()).hexdigest()
        self.ledger = output / "exact-checks.jsonl"
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                record = json.loads(line)
                if record.get("source_sha256") != self.source_hash:
                    raise ValueError("native source changed; use a new output directory")
                if record["status"] == "complete":
                    self._accept(record)
                elif not retry_timeouts:
                    self.attempted.add(key(record["position"]))

    def _accept(self, row):
        gs = tuple(row["position"])
        evidence = {"kind": "native-exact", "source": str(self.ledger),
                    "source_sha256": row["source_sha256"],
                    "frobenius": row["frobenius"], "states": row["states"],
                    "winning_move": row["winning_move"]}
        for field in ("native_words", "mode", "states_are_cumulative"):
            if field in row:
                evidence[field] = row[field]
        self.graph.add_fact(gs, row["outcome"], evidence)
        if row["winning_move"] is not None:
            self.graph.add_fact((*gs, row["winning_move"]), "P",
                                {**evidence, "kind": "native-winning-destination",
                                 "parent": key(gs)})

    def solve(self, generators, seconds=5):
        gs = minimal_generators(generators)
        k = key(gs)
        if k in self.graph.facts:
            return self.graph.facts[k]
        if k in self.attempted or self.remaining <= 0 or gcd(*gs) != 1:
            return None
        self.attempted.add(k)
        frob = frobenius_number(gs)
        if frob > 1023:
            return None
        words = next(w for w in (1, 2, 4, 8, 16) if frob < 64 * w)
        binary = compile_solver(words, self.build)
        command = [str(binary), *map(str, gs)]
        start = time.monotonic()
        row = {"position": gs, "source_sha256": self.source_hash, "native_words": words}
        try:
            proc = subprocess.run(
                ["bash", "-c", "ulimit -v 4194304 && exec " + shlex.join(command)],
                capture_output=True, text=True, timeout=min(seconds, self.remaining))
            match = NATIVE_ROW.fullmatch(proc.stdout.strip()) if proc.returncode == 0 else None
            if match:
                outcome, winner, found_frob, states = match.groups()
                winner = None if winner == "none" else int(winner)
                if int(found_frob) != frob or (outcome == "P") != (winner is None):
                    raise ValueError("native output failed arithmetic/outcome check")
                if winner is not None and (winner < 2 or is_generated(gs, winner)):
                    raise ValueError("native output has an illegal winning move")
                row.update(status="complete", outcome=outcome, winning_move=winner,
                           frobenius=frob, states=int(states))
            else:
                row.update(status="failed", returncode=proc.returncode,
                           stderr=proc.stderr[-500:])
        except subprocess.TimeoutExpired:
            row["status"] = "timeout"
        row["elapsed_seconds"] = time.monotonic() - start
        self.remaining -= row["elapsed_seconds"]
        with self.ledger.open("a") as handle:
            handle.write(json.dumps(row) + "\n")
        if row["status"] == "complete":
            self._accept(row)
        return self.graph.facts.get(k)


def claim_target(claim):
    gs = minimal_generators(claim["position"])
    if claim["kind"] == "winning-reply":
        reply = claim["reply"]
        if reply < 2 or is_generated(gs, reply):
            return None
        return minimal_generators((*gs, reply))
    return gs


def audit_derived(graph):
    """Recheck generated proof steps with elementary semigroup arithmetic."""
    counts = Counter()
    for k, fact in graph.facts.items():
        gs = position(k)
        ev = fact["evidence"]
        kind = ev["kind"]
        if kind == "winning-edge":
            move = ev["move"]
            if move < 2 or is_generated(gs, move):
                raise ValueError(f"illegal proof edge at {k}")
            dest = key((*gs, move))
            if dest != ev["destination"] or graph.facts[dest]["outcome"] != "P":
                raise ValueError(f"unsupported N proof at {k}")
        elif kind == "complete-cover":
            info = profile(gs)
            if not info["complete_moves"] or ev["tail"] != info["tail"]:
                raise ValueError(f"unsupported infinite coverage at {k}")
            rows = ev["obligations"]
            if sorted(r["move"] for r in rows) != info["moves"]:
                raise ValueError(f"incomplete proof at {k}")
            for row in rows:
                dest = key((*gs, row["move"]))
                if dest != row["destination"] or graph.facts[dest]["outcome"] != "N":
                    raise ValueError(f"unsupported P proof at {k}")
        elif kind == "quiet-ender-theorem":
            finite = FiniteSolver(gs)
            if finite.frobenius <= 1 or not finite.is_quiet_ender():
                raise ValueError(f"invalid quiet-ender theorem at {k}")
        else:
            continue
        counts[kind] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--cache", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exact-budget", type=float, default=300)
    parser.add_argument("--public-list", type=Path)
    parser.add_argument("--extra-targets", type=Path,
                        help="JSON list of additional positions to inspect, never accepted as facts")
    parser.add_argument("--focus-public", action="store_true",
                        help="reserve new exact work for the September 3 public node")
    parser.add_argument("--retry-timeouts", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    corpus = json.loads(args.claims.read_text())
    claims = corpus["claims"]
    graph = ProofGraph()
    for index, cache in enumerate(args.cache):
        snapshot = args.output / f"input-cache-{index}.cache"
        if not snapshot.exists():
            snapshot.write_bytes(cache.read_bytes())
        print("CACHE", cache, graph.load_exact_cache(snapshot), flush=True)
    graph.seed_repository()
    checker = ExactChecks(graph, args.output, args.exact_budget, args.retry_timeouts)

    # First reproduce the original explicit-claim check, with a real bound.
    explicit = [c for c in claims if c["location"].startswith("explicit:")]
    for claim in ([] if args.focus_public else explicit):
        target = claim_target(claim)
        if target and gcd(*target) == 1:
            checker.solve(target, seconds=5)
    print("EXPLICIT checked; budget left", round(checker.remaining, 1), flush=True)

    candidates = {NEW_PUBLIC}
    if args.extra_targets:
        candidates.update(minimal_generators(gs) for gs in json.loads(args.extra_targets.read_text()))
    hints = defaultdict(set)
    for claim in claims:
        target = claim_target(claim)
        if target is None:
            continue
        if claim["kind"] == "winning-reply":
            hints[key(claim["position"])].add(claim["reply"])
        if gcd(*target) == 2 and (16 in target or claim in explicit):
            candidates.add(target)
    if args.public_list:
        for match in re.finditer(r"\{(\d+(?:,\s*\d+)+)\}", args.public_list.read_text()):
            gs = minimal_generators(map(int, match[1].split(",")))
            if 16 in gs and gcd(*gs) == 2:
                candidates.add(gs)
    # Candidate source assertions supply targets/hints only, never facts.
    candidates = sorted(candidates, key=lambda p: (p != NEW_PUBLIC,
                         profile(p).get("half_frobenius", 10000), p))
    print("CANDIDATES", len(candidates), flush=True)
    graph.close(candidates)
    check_candidates = [NEW_PUBLIC] if args.focus_public else candidates

    for round_number in range(3):
        before = len(graph.facts)
        for target in check_candidates:
            node = graph.inspect(target)
            if node["outcome"] != "unknown" or not profile(target)["complete_moves"]:
                continue
            for move in node["open_moves"]:
                child = minimal_generators((*target, move))
                if gcd(*child) == 1:
                    checker.solve(child, seconds=30 if args.focus_public else 3)
                else:
                    for reply in sorted(hints.get(key(child), ())):
                        dest = minimal_generators((*child, reply))
                        if gcd(*dest) == 1:
                            checker.solve(dest, seconds=3)
                            if graph.route(child):
                                break
            graph.inspect(target)
        graph.close(candidates)
        print("ROUND", round_number + 1, "proved candidates",
              sum(key(p) in graph.facts and graph.facts[key(p)]["outcome"] == "P"
                  for p in candidates), "budget left", round(checker.remaining, 1), flush=True)
        if len(graph.facts) == before or checker.remaining <= 0:
            break

    # Spend any remaining initial budget on the specifically selected new
    # public certificate, not an eleven-way scan of opening grandchildren.
    node = graph.inspect(NEW_PUBLIC)
    if node["outcome"] == "unknown":
        for move in node["open_moves"]:
            child = minimal_generators((*NEW_PUBLIC, move))
            if gcd(*child) == 1:
                continue
            for reply in range(3, 150, 2):
                if checker.remaining <= 0 or graph.route(child):
                    break
                checker.solve((*child, reply), seconds=2)
            print("PUBLIC CHILD", move, graph.facts.get(key(child), {}).get("outcome", "unknown"),
                  "budget left", round(checker.remaining, 1), flush=True)
        graph.close(candidates)

    base = (16, 26)
    children = [minimal_generators((*base, move)) for move in profile(base)["even_moves"]]
    later = [(16, m) for m in range(28, 63, 2) if m % 16]
    targets = [base, (16, 26, 88), (16, 26, 82, 88), (16, 26, 88, 98),
               (16, 26, 62, 98), *children, *later]
    graph.close([*candidates, *targets])

    checked = []
    for claim in claims:
        dest = claim_target(claim)
        fact = graph.facts.get(key(dest)) if dest else None
        status = ("illegal-reply" if dest is None else "pending" if fact is None
                  else "verified" if fact["outcome"] == "P" else "contradicted")
        checked.append({**claim, "target": dest, "verification": status})
    counts = dict(Counter(c["verification"] for c in checked))
    explicit_counts = dict(Counter(c["verification"] for c in checked
                                  if c["location"].startswith("explicit:")))
    audit = audit_derived(graph)
    graph.export(args.output / "proof-graph.json", {
        "privacy": "private source-derived graph; do not publish",
        "claim_source_hashes": corpus["sources"], "claim_counts": counts,
        "explicit_claim_counts": explicit_counts, "derived_step_audit": audit,
        "residual_U_constraint": {
            "U": "16,26,88", "X": "16,26,82,88", "Q": "16,26,88,98",
            "P_requires": {"16,26,82,88": "N", "16,26,88,98": "N"},
            "warning": "X N alone does not prove U P; Q+82=X only proves Q N when X is P"},
        "tool_sha256": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                        for name in ("proof_graph.py", "import_claims.py", "reconcile_campaign.py",
                                     "native_solver.cpp", "short_certificates.py")},
        "claims_sha256": hashlib.sha256(args.claims.read_bytes()).hexdigest(),
        "extra_targets_sha256": (hashlib.sha256(args.extra_targets.read_bytes()).hexdigest()
                                 if args.extra_targets else None),
        "public_list_sha256": (hashlib.sha256(args.public_list.read_bytes()).hexdigest()
                               if args.public_list else None)})
    (args.output / "verified-claims.json").write_text(json.dumps(checked, indent=2) + "\n")

    ranking = []
    for target in targets:
        node = graph.nodes[key(target)]
        info = profile(minimal_generators(target))
        unresolved = node.get("open_moves", [])
        is_opening_reply = target == base or target in later
        consequence = ("P settles opening 16; N excludes this reply" if is_opening_reply
                       else "P answers move 26; N removes a candidate")
        if target == (16, 26, 82, 88):
            consequence = "P proves U N; N leaves Q N required before U P and reply 88"
        elif target == (16, 26, 88, 98):
            consequence = "P proves U N; N leaves X N required before U P and reply 88"
        elif target == (16, 26, 62, 98):
            consequence = "P proves Q N and refutes child 98 of {16,26}; N leaves both open"
        first_unknown_odd = None
        if info["gcd"] == 2 and not info.get("quiet", False) and node["outcome"] == "unknown":
            first_unknown_odd = next((m for m in range(3, 410, 2)
                                      if key((*target, m)) not in graph.facts), None)
        ranking.append({"position": list(target), "outcome": node["outcome"],
                        "tail": info["tail"], "half_frobenius": info.get("half_frobenius"),
                        "open_moves": unresolved,
                        "unknown_children": [key((*target, m)) for m in unresolved],
                        "first_uncached_odd_through_409": first_unknown_odd,
                        "consequence": consequence,
                        "priority_key": [0 if is_opening_reply else 1,
                                         0 if info["complete_moves"] else 1,
                                         len(unresolved), info.get("half_frobenius", 10000)]})
    ranking.sort(key=lambda r: (r["outcome"] != "unknown", r["priority_key"], r["position"]))
    (args.output / "target-ranking.json").write_text(json.dumps(ranking, indent=2) + "\n")
    print("CLAIMS", counts, "EXPLICIT", explicit_counts, "AUDIT", audit, flush=True)
    for target in [NEW_PUBLIC, base, (16, 26, 88), (16, 26, 82, 88)]:
        n = graph.nodes[key(target)]
        print("RESULT", target, n["outcome"], "open", n.get("open_moves"), flush=True)


if __name__ == "__main__":
    main()
