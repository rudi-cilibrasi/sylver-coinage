#!/usr/bin/env python3
"""Recompute every finite leaf of B's certificate with an empty native memo.

No campaign outcome cache is loaded. The named infinite P certificates and
the Quiet End Theorem remain explicit dependencies, as in verify_pairs.py.
"""
import argparse
import hashlib
import json
from math import gcd
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "sylver/publication/plan2-2026-09-05"))
from sylver.proof_graph import ProofGraph, key
from sylver.reconcile_campaign import audit_derived
from sylver.short_certificates import is_generated
from sylver.solver import frobenius_number

ROW = re.compile(r"position=([\d,]+) ([PN]) winning_move=(none|\d+) "
                 r"frobenius=(\d+) cumulative_states=(\d+)")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "b-verification")
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument("--memory-gib", type=int, default=10)
    args = parser.parse_args()
    if min(args.seconds, args.memory_gib) <= 0:
        parser.error("limits must be positive")
    args.output.mkdir()  # Preserve earlier verification runs.
    certificate = HERE / "b-certificate.json"
    data = json.loads(certificate.read_text())
    graph = ProofGraph()
    known = ProofGraph()
    known.seed_repository()
    finite, dependencies, visited, active = {}, {}, set(), set()
    for k, fact in data["support"].items():
        gs = tuple(map(int, k.split(',')))
        if key(gs) != k:
            raise ValueError("noncanonical certificate position")
        graph.add_fact(gs, fact["outcome"], fact["evidence"])

    def visit(k):
        if k in active:
            raise ValueError("cyclic certificate")
        if k in visited:
            return
        active.add(k)
        fact = graph.facts[k]
        ev = fact["evidence"]
        gs = tuple(map(int, k.split(',')))
        if ev["kind"] == "winning-edge":
            visit(ev["destination"])
        elif ev["kind"] == "complete-cover":
            for row in ev["obligations"]:
                visit(row["destination"])
        elif gcd(*gs) == 1:
            finite[k] = fact["outcome"]
        elif (fact["outcome"] == "P" and ev["kind"] == "repository-certificate"
              and known.facts.get(k) == fact):
            dependencies[k] = ev["source"]
        else:
            raise ValueError(f"unsupported infinite leaf {k}")
        active.remove(k)
        visited.add(k)

    for root in data["roots"]:
        visit(root)
    if visited != set(graph.facts):
        raise ValueError("unreachable certificate support")
    structural_audit = audit_derived(graph)
    positions = sorted(finite, key=lambda k: (frobenius_number(tuple(map(int, k.split(',')))), k))
    bound = max(frobenius_number(tuple(map(int, k.split(',')))) for k in positions)
    words = bound // 64 + 1
    source = ROOT / "sylver/native_solver.cpp"
    build = args.output / "build"
    build.mkdir()
    binary = build / "native"
    subprocess.run(["g++", "-std=c++20", "-O3", "-Wall", "-Wextra", "-pedantic",
                    f"-DSYLVER_NATIVE_WORDS={words}", str(source), "-o", str(binary)], check=True)
    requests = args.output / "positions.txt"
    requests.write_text('\n'.join(positions) + '\n')
    command = [str(binary), "--batch-file", str(requests)]

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (args.memory_gib * 1024**3,) * 2)

    start = time.monotonic()
    stdout, stderr = args.output / "stdout.txt", args.output / "stderr.txt"
    with stdout.open('w') as out, stderr.open('w') as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, preexec_fn=cap)
        print("VERIFY-B", "finite leaves", len(positions), "pid", process.pid, flush=True)
        timed_out = False
        try:
            process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
    rows = []
    previous_states = 0
    for i, line in enumerate(stdout.read_text().splitlines()):
        match = ROW.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed native result: {line}")
        k, outcome, winner, f, states = match.groups()
        gs = tuple(map(int, k.split(',')))
        move = None if winner == 'none' else int(winner)
        if (i >= len(positions) or k != positions[i] or outcome != finite[k]
                or int(f) != frobenius_number(gs) or int(states) < previous_states
                or (outcome == 'P') != (move is None)
                or move is not None and (move < 2 or is_generated(gs, move))):
            raise ValueError(f"finite replay disagrees: {line}")
        previous_states = int(states)
        rows.append({"position": gs, "outcome": outcome, "winning_move": move,
                     "frobenius": int(f), "cumulative_states": int(states)})
    complete = process.returncode == 0 and len(rows) == len(positions)
    report = {"status": "verified" if complete else "incomplete",
              "roots": {k: graph.facts[k]["outcome"] for k in data["roots"]},
              "structural_audit": structural_audit, "checked_nodes": len(visited),
              "finite_requested": len(positions), "finite_completed": len(rows),
              "native_words": words, "finite_replays": rows,
              "named_repository_dependencies": dependencies,
              "certificate_sha256": digest(certificate), "source_sha256": digest(source),
              "verifier_sha256": digest(Path(__file__)), "command": command,
              "requests_sha256": digest(requests), "stdout_sha256": digest(stdout),
              "elapsed_seconds": time.monotonic() - start,
              "returncode": process.returncode, "timed_out": timed_out,
              "scope": "All finite leaves replayed from an empty shared memo; no inherited outcome cache. Infinite certificates and Quiet End Theorem remain explicit dependencies."}
    (args.output / "receipt.json").write_text(json.dumps(report, indent=2) + '\n')
    print(report["status"], len(rows), '/', len(positions), flush=True)
    if not complete:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
