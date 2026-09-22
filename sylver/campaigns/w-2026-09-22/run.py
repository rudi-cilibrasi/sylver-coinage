#!/usr/bin/env python3
"""Reconstruct and advance W using the frozen September 5 research tools.

Run from any directory. The campaign cache is read-only; new computations
are recorded separately. A scan limit or timeout never supplies an outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "sylver/publication/plan2-2026-09-05"
sys.path.insert(0, str(BUNDLE))

from sylver.proof_graph import ProofGraph, key, position, profile
from sylver.focus_campaign import restore
from sylver.reconcile_campaign import ExactChecks, audit_derived
from sylver.short_certificates import minimal_generators

W = (16, 26, 62, 98)
PUBLISHED = (16, 26, 62, 72, 82)
PUBLISHED_URL = "https://sicherman.net/sylver/ppos.html"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=float, default=300,
                        help="total native runtime budget for this invocation")
    parser.add_argument("--seconds", type=float, default=3,
                        help="native runtime limit per position; address space is 4 GiB")
    parser.add_argument("--odd-limit", type=int, default=201)
    parser.add_argument("--retry-timeouts", action="store_true")
    args = parser.parse_args()
    if args.budget < 0 or args.seconds <= 0 or args.odd_limit < 3:
        parser.error("invalid computation limits")
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    cache = ROOT / "sylver/move26_data/periodicity_x.cache"
    certificate = BUNDLE / "evidence/certificate.json"
    inputs = {
        "cache": {"path": str(cache.relative_to(ROOT)), "sha256": digest(cache)},
        "certificate": {"path": str(certificate.relative_to(ROOT)),
                        "sha256": digest(certificate)},
        "tools": {name: digest(BUNDLE / "sylver" / name) for name in
                  ("proof_graph.py", "reconcile_campaign.py", "solver.py",
                   "short_certificates.py", "native_solver.cpp", "parallel_solve.py")},
        "published_assumption": {"position": PUBLISHED, "outcome": "P",
                                 "url": PUBLISHED_URL, "consulted": "2026-09-22"},
    }
    manifest = args.output / "inputs.json"
    serialized = json.dumps(inputs, indent=2, sort_keys=True) + "\n"
    if manifest.exists() and manifest.read_text() != serialized:
        raise ValueError("inputs changed; use a separate output directory")
    manifest.write_text(serialized)

    saved = args.output / "proof-graph.json"
    if saved.exists():
        # Preserve discoveries from the mixed-position batch continuation.
        graph, _ = restore(saved)
    else:
        graph = ProofGraph()
        graph.seed_repository()
        graph.load_exact_cache(cache)
    for k, fact in json.loads(certificate.read_text())["facts"].items():
        graph.add_fact(position(k), fact["outcome"], {
            "kind": "inherited-release-certificate", "source": str(certificate),
            "sha256": inputs["certificate"]["sha256"], "original_kind": fact["kind"],
        })
    graph.add_fact(PUBLISHED, "P", {"kind": "published-assumption", "url": PUBLISHED_URL})
    checker = ExactChecks(graph, args.output, args.budget, args.retry_timeouts)

    def checkpoint():
        node = graph.inspect(W)
        report = {
            "target": W, "outcome": node["outcome"],
            "open_moves": node.get("open_moves", []),
            "native_budget_remaining": checker.remaining,
            "odd_search_limit": args.odd_limit,
            "audit": audit_derived(graph),
            "scope": "Inherited exact cache, repository certificates, September 5 "
                     "release, and the explicitly named published P assumption. "
                     "Only exact-checks.jsonl contains fresh computations.",
        }
        graph.export(args.output / "proof-graph.tmp", report)
        (args.output / "proof-graph.tmp").replace(args.output / "proof-graph.json")
        (args.output / "frontier.json").write_text(json.dumps(report, indent=2) + "\n")
        print("FRONTIER", node["outcome"], node.get("open_moves", []),
              "budget", round(checker.remaining, 2), flush=True)
        return node

    node = checkpoint()
    # First reconstruct the finite exceptional odd side; historical prose
    # stating it is complete is deliberately not imported as a proof leaf.
    for move in profile(W)["exceptional_odds"]:
        child = minimal_generators((*W, move))
        if not graph.route(child):
            fact = checker.solve(child, args.seconds)
            print("ODD", move, fact["outcome"] if fact else "unknown", flush=True)
    node = checkpoint()
    # Interleave the even obligations so one hard branch cannot consume the
    # entire budget. Routes into already-known P positions have no move cutoff.
    for odd in range(3, args.odd_limit + 1, 2):
        if checker.remaining <= 0 or graph.route(W):
            break
        for even in profile(W)["even_moves"]:
            child = minimal_generators((*W, even))
            if graph.route(child):
                continue
            target = minimal_generators((*child, odd))
            if graph.route(target):
                continue
            fact = checker.solve(target, args.seconds)
            print("CHECK", even, odd, fact["outcome"] if fact else "unknown", flush=True)
            if fact and fact["outcome"] == "P":
                checkpoint()
            if checker.remaining <= 0:
                break
        if odd % 20 == 1:
            checkpoint()
    checkpoint()


if __name__ == "__main__":
    main()
