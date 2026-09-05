"""Resume a proof graph and search selected obligations under a time budget.

Odd scans are witness searches only. A long position never becomes P from
exhausting --odd-limit. Short successors use complete Quiet End coverage.
Keep outputs private when the input graph contains unpublished evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from math import gcd
from pathlib import Path

from sylver.proof_graph import ProofGraph, key, position, profile
from sylver.reconcile_campaign import ExactChecks, audit_derived
from sylver.short_certificates import minimal_generators


def restore(path):
    data = path.read_bytes()
    seed = json.loads(data)
    graph = ProofGraph()
    for name, source in seed["sources"].items():
        cache = Path(name)
        if hashlib.sha256(cache.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"seed cache changed: {cache}")
        graph.load_exact_cache(cache)
    graph.seed_repository()
    for name, fact in seed["support"].items():
        graph.add_fact(position(name), fact["outcome"], fact["evidence"])
    graph.nodes.update(seed.get("nodes", {}))
    audit_derived(graph)
    return graph, hashlib.sha256(data).hexdigest()


def frontier(graph, root, moves):
    """Root children and their short even successors, all deduplicated."""
    info = profile(root)
    if info["gcd"] != 2 or "even_moves" not in info:
        raise ValueError("target must be a nonterminal gcd-two position")
    if any(m not in info["even_moves"] for m in moves):
        raise ValueError("child moves must be legal even moves of the target")
    children = {minimal_generators((*root, m)) for m in moves}
    short = set()
    for child in children:
        if graph.route(child):
            continue
        if profile(child).get("quiet"):
            short.add(child)
        else:
            for reply in profile(child).get("even_moves", []):
                dest = minimal_generators((*child, reply))
                if profile(dest).get("quiet"):
                    short.add(dest)
    return children, short


def pending_checks(graph, children, short, odd_limit, hints=None):
    """Finite obligations only; routing always precedes expensive evaluation."""
    pending = set()
    hinted = set()
    # Avoid spending on successors after their parent has been settled.
    needed_short = set()
    for child in children:
        if graph.route(child):
            continue
        for move in (hints or {}).get(key(child), ()):
            if move <= 1:
                continue
            dest = minimal_generators((*child, move))
            if gcd(*dest) == 1 and not graph.route(dest):
                hinted.add(dest)
                pending.add(dest)
        if child in short:
            needed_short.add(child)
        else:
            for move in range(3, odd_limit + 1, 2):
                dest = minimal_generators((*child, move))
                if not graph.route(dest):
                    pending.add(dest)
            for move in profile(child).get("even_moves", []):
                dest = minimal_generators((*child, move))
                if dest in short:
                    needed_short.add(dest)
    for target in needed_short:
        node = graph.inspect(target)
        if node["outcome"] != "unknown":
            continue
        for move in node["open_moves"]:
            dest = minimal_generators((*target, move))
            if gcd(*dest) == 1 and not graph.route(dest):
                pending.add(dest)
    return sorted(pending, key=lambda p: (p not in hinted, profile(p)["frobenius"], -len(p), p))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=position, required=True)
    parser.add_argument("--child-moves", type=position, required=True)
    parser.add_argument("--context", type=position, action="append", default=[])
    parser.add_argument("--claims", type=Path, help="attributed reply hints, never accepted as facts")
    parser.add_argument("--odd-limit", type=int, default=129)
    parser.add_argument("--exact-budget", type=float, default=300)
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--retry-timeouts", action="store_true")
    args = parser.parse_args()
    if args.seconds <= 0 or args.exact_budget < 0:
        parser.error("seconds must be positive and budget nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    graph, seed_hash = restore(args.seed)
    # Bind a resumed directory to its original input instead of silently
    # mixing two different proof corpora in a single ledger.
    manifest_path = args.output / "seed.json"
    manifest = {"path": str(args.seed.resolve()), "sha256": seed_hash}
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        raise ValueError("output directory belongs to another seed graph")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    checker = ExactChecks(graph, args.output, args.exact_budget, args.retry_timeouts)
    hints = defaultdict(set)
    if args.claims:
        for claim in json.loads(args.claims.read_text())["claims"]:
            if claim['kind'] == 'winning-reply':
                hints[key(claim['position'])].add(claim['reply'])
    root = minimal_generators(args.target)
    children, short = frontier(graph, root, args.child_moves)
    # A short root may itself have missing finite odd obligations. Include
    # them even when the requested child focus contains only even moves.
    if profile(root).get("quiet"):
        children.add(root)
        short.add(root)
    all_children = {minimal_generators((*root, m)) for m in profile(root)["even_moves"]}
    targets = {root, *all_children, *short, *map(tuple, args.context),
               *(position(k) for k in graph.nodes)}
    graph.close(targets)
    run = {"seed": manifest, "target": list(root),
           "child_moves": list(args.child_moves), "odd_search_limit": args.odd_limit,
           "native_budget_seconds": args.exact_budget, "per_check_seconds": args.seconds,
           "warning": "a finite odd search never certifies a long position P",
           "claims": {"path": str(args.claims.resolve()),
                      "sha256": hashlib.sha256(args.claims.read_bytes()).hexdigest()} if args.claims else None,
           "tools": {name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                     for name in ("focus_campaign.py", "proof_graph.py", "reconcile_campaign.py",
                                  "native_solver.cpp", "short_certificates.py")}}

    def checkpoint():
        graph.close(targets)
        report = {**run, "budget_remaining": checker.remaining,
                  "derived_step_audit": audit_derived(graph)}
        graph.export(args.output / "proof-graph.tmp", report)
        (args.output / "proof-graph.tmp").replace(args.output / "proof-graph.json")
        print("TARGET", key(root), graph.nodes[key(root)].get("open_moves", []),
              graph.nodes[key(root)]["outcome"], "budget", round(checker.remaining, 1), flush=True)

    checkpoint()
    completed_since_checkpoint = 0
    while checker.remaining > 0 and not graph.route(root):
        jobs = [p for p in pending_checks(graph, children, short, args.odd_limit, hints)
                if key(p) not in checker.attempted and profile(p)["frobenius"] <= 1023]
        if not jobs:
            break
        # Rebuild routing only when new P destinations can change obligations.
        version = graph.p_version
        for job in jobs:
            if checker.remaining <= 0 or graph.route(root):
                break
            if graph.route(job):
                continue
            fact = checker.solve(job, args.seconds)
            completed_since_checkpoint += 1
            print("CHECK", key(job), fact["outcome"] if fact else "unknown",
                  fact["evidence"].get("winning_move") if fact else None,
                  "budget", round(checker.remaining, 1), flush=True)
            if graph.p_version != version or completed_since_checkpoint >= 10:
                checkpoint()
                completed_since_checkpoint = 0
            if graph.p_version != version:
                break
    checkpoint()


if __name__ == "__main__":
    main()
