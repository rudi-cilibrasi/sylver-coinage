#!/usr/bin/env python3
"""Continue W with cross-branch transpositions in the exact native solver."""

import argparse
import hashlib
import json
from math import gcd
from pathlib import Path
import re
import resource
import subprocess
import time

from run import ROOT, W, key, minimal_generators, profile
from sylver.focus_campaign import restore
from sylver.reconcile_campaign import audit_derived
from sylver.short_certificates import is_generated
from sylver.solver import frobenius_number

ROW = re.compile(r"position=([\d,]+) ([PN]) winning_move=(none|\d+) "
                 r"frobenius=(\d+) cumulative_states=(\d+)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", help="comma-separated gcd-two root; defaults to W")
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--odd-limit", type=int, default=101)
    parser.add_argument("--max-positions", type=int, default=100)
    parser.add_argument("--memory-gib", type=int, default=4)
    parser.add_argument("--hints", default="", help="comma-separated root replies to try first")
    args = parser.parse_args()
    if min(args.seconds, args.max_positions, args.memory_gib) <= 0 or args.odd_limit < 3:
        parser.error("invalid resource or search limits")
    output = args.output.resolve()
    target = minimal_generators(tuple(map(int, args.target.split(',')))) if args.target else W
    hints = tuple(map(int, args.hints.split(','))) if args.hints else ()
    if any(move < 2 for move in hints):
        parser.error("hints must be legal-sized positive moves")
    if gcd(*target) != 2 or target == (2,):
        parser.error("target must be a nonterminal gcd-two position")
    graph, seed_hash = restore(output / "proof-graph.json")
    wanted = set()
    for odd in profile(target)["exceptional_odds"]:
        p = minimal_generators((*target, odd))
        if not graph.route(p):
            wanted.add(p)
    for even in profile(target)["even_moves"]:
        child = minimal_generators((*target, even))
        if graph.route(child):
            continue
        for odd in range(3, args.odd_limit + 1, 2):
            p = minimal_generators((*child, odd))
            if not graph.route(p):
                wanted.add(p)
    positions = sorted(wanted, key=lambda p: (frobenius_number(p), p))[:args.max_positions]
    if not positions:
        print("No pending finite candidates in this search range.")
        return
    bound = max(frobenius_number(p) for p in positions)
    words = bound // 64 + 1
    if words > 32:
        raise ValueError("requested positions exceed the 2047-bit Frobenius limit")
    index = 1
    while (output / f"batch-{index:04d}").exists():
        index += 1
    run = output / f"batch-{index:04d}"
    run.mkdir()
    source = ROOT / "sylver/native_solver.cpp"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    build = output / "build"
    build.mkdir(exist_ok=True)
    binary = build / f"batch-{source_hash[:16]}-w{words}"
    if not binary.exists():
        subprocess.run(["g++", "-std=c++20", "-O3", "-Wall", "-Wextra",
                        "-pedantic", f"-DSYLVER_NATIVE_WORDS={words}",
                        str(source), "-o", str(binary)], check=True)
    requests = run / "positions.txt"
    requests.write_text("\n".join(key(p) for p in positions) + "\n")

    def cap_memory():
        limit = args.memory_gib * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    start = time.monotonic()
    command = [str(binary)]
    if hints:
        command += ["--hints", ",".join(map(str, hints))]
    command += ["--batch-file", str(requests)]
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, preexec_fn=cap_memory)
    print("BATCH", index, "positions", len(positions), "pid", process.pid, flush=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=args.seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    elapsed = time.monotonic() - start
    (run / "stdout.txt").write_text(stdout)
    (run / "stderr.txt").write_text(stderr)
    rows = []
    previous_states = 0
    for i, line in enumerate(stdout.splitlines()):
        match = ROW.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed native row: {line}")
        k, outcome, winner, f, states = match.groups()
        gs = tuple(map(int, k.split(',')))
        winner = None if winner == "none" else int(winner)
        if (i >= len(positions) or gs != positions[i]
                or int(f) != frobenius_number(gs)
                or (outcome == "P") != (winner is None)
                or int(states) < previous_states
                or (winner is not None and (winner < 2 or is_generated(gs, winner)))):
            raise ValueError(f"invalid native row: {line}")
        previous_states = int(states)
        evidence = {"kind": "native-batch", "source": str(run / "stdout.txt"),
                    "source_sha256": source_hash, "native_words": words,
                    "frobenius": int(f),
                    "cumulative_states": int(states), "winning_move": winner}
        graph.add_fact(gs, outcome, evidence)
        if winner is not None:
            graph.add_fact((*gs, winner), "P", {**evidence,
                           "kind": "native-batch-winning-destination", "parent": k})
        rows.append({"position": gs, "outcome": outcome, **evidence})
        print("RESULT", k, outcome, winner, flush=True)
    receipt = {"seed_sha256": seed_hash, "source_sha256": source_hash,
               "native_words": words,
               "hints": hints, "command": command,
               "requests_sha256": hashlib.sha256(requests.read_bytes()).hexdigest(),
               "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
               "elapsed_seconds": elapsed, "returncode": process.returncode,
               "timed_out": timed_out, "memory_gib": args.memory_gib,
               "requested": len(positions), "completed": len(rows),
               "rows": rows}
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    # New finite leaves can close a previously inspected short subsidiary
    # position, which can in turn settle a parent through an even reply.
    graph.close([target, *(tuple(map(int, k.split(','))) for k in graph.nodes)])
    node = graph.inspect(target)
    report = {"target": target, "outcome": node["outcome"],
              "open_moves": node.get("open_moves", []), "audit": audit_derived(graph),
              "last_batch": str(run),
              "scope": "Inherited facts retain their named dependencies. Batch "
                       "outcomes are fresh exact computations with a shared memo; "
                       "state counts are cumulative. Unfinished requests remain unknown."}
    graph.export(output / "proof-graph.tmp", report)
    (output / "proof-graph.tmp").replace(output / "proof-graph.json")
    (output / "frontier.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FRONTIER", report["outcome"], report["open_moves"], flush=True)


if __name__ == "__main__":
    main()
