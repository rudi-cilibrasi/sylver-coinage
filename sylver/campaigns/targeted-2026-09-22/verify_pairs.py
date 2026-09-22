#!/usr/bin/env python3
"""Replay the compact pair certificates without loading the campaign cache.

Finite leaves use independent, fresh Python memo tables. Named repository P
certificates and the Quiet End Theorem are explicit mathematical dependencies.
"""

import argparse
import gc
import hashlib
import json
from math import gcd
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "sylver/publication/plan2-2026-09-05"))
from sylver.proof_graph import ProofGraph, key, profile
from sylver.short_certificates import is_generated
from sylver.solver import FiniteSolver
import sylver.solver as reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, default=HERE / "pair-certificates.json")
    parser.add_argument("--output", type=Path, default=HERE / "pair-verification.json")
    args = parser.parse_args()
    data = args.certificate.read_bytes()
    certificate = json.loads(data)
    facts = certificate["support"]
    known = ProofGraph()
    known.seed_repository()
    checked, active, finite, dependencies = set(), set(), [], {}
    started = time.monotonic()

    def visit(k):
        if k in active:
            raise ValueError(f"circular certificate at {k}")
        if k in checked:
            return
        gs = tuple(map(int, k.split(',')))
        if key(gs) != k:
            raise ValueError(f"noncanonical position {k}")
        active.add(k)
        fact = facts[k]
        outcome, evidence = fact["outcome"], fact["evidence"]
        kind = evidence["kind"]
        if kind == "winning-edge":
            move = evidence["move"]
            dest = key((*gs, move))
            if outcome != "N" or move < 2 or is_generated(gs, move):
                raise ValueError(f"invalid winning move at {k}")
            if dest != evidence["destination"] or facts[dest]["outcome"] != "P":
                raise ValueError(f"wrong winning destination at {k}")
            visit(dest)
        elif kind == "complete-cover":
            info = profile(gs)
            rows = evidence["obligations"]
            if (outcome != "P" or not info["complete_moves"]
                    or evidence["tail"] != info["tail"]
                    or sorted(r["move"] for r in rows) != info["moves"]):
                raise ValueError(f"incomplete move coverage at {k}")
            for row in rows:
                dest = key((*gs, row["move"]))
                if dest != row["destination"] or facts[dest]["outcome"] != "N":
                    raise ValueError(f"wrong cover destination at {k}")
                visit(dest)
        elif gcd(*gs) == 1:
            start = time.monotonic()
            result = FiniteSolver(gs).solve()
            actual = "N" if result.is_winning else "P"
            if actual != outcome:
                raise ValueError(f"finite replay disagrees at {k}: {actual}")
            finite.append({"position": gs, "outcome": actual,
                           "winning_move": result.winning_move,
                           "frobenius": result.frobenius,
                           "states": result.states_evaluated,
                           "seconds": time.monotonic() - start})
            print(k, actual, result.states_evaluated, flush=True)
            gc.collect()
        else:
            expected = known.facts.get(k)
            if (outcome != "P" or kind != "repository-certificate"
                    or expected != fact):
                raise ValueError(f"unsupported infinite leaf at {k}")
            dependencies[k] = evidence["source"]
        active.remove(k)
        checked.add(k)

    for root in certificate["roots"]:
        visit(root)
    if checked != set(facts):
        raise ValueError("certificate contains unreachable support")
    report = {"status": "verified", "roots": {k: facts[k]["outcome"]
               for k in certificate["roots"]}, "checked_nodes": len(checked),
              "certificate_sha256": hashlib.sha256(data).hexdigest(),
              "python_solver_sha256": hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest(),
              "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "elapsed_seconds": time.monotonic() - started,
              "finite_replays": finite, "named_repository_dependencies": dependencies,
              "theorem": "Quiet End Theorem for the short complete covers",
              "scope": "All finite leaves independently recomputed with fresh Python memos; named infinite certificates remain dependencies."}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("VERIFIED", len(checked), "nodes;", len(finite), "finite leaves;",
          len(dependencies), "named repository certificates", flush=True)


if __name__ == "__main__":
    main()
