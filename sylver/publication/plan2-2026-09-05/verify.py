"""Audit certificate structure and recompute every finite leaf by default."""
import argparse
import hashlib
import json
import re
import resource
import subprocess
import tempfile
from collections import Counter
from math import gcd
from pathlib import Path

from sylver.periodicity import analyze_odd_tail
from sylver.solver import solve_position

HERE = Path(__file__).resolve().parent
PUBLIC_THEOREMS = {
    (8, 12), (8, 10, 22), (8, 10, 12, 14),
    (8, 12, 18, 22), (8, 12, 26, 30),
}
ROW = re.compile(r"([PN]) winning_move=(none|\d+) frobenius=(\d+) states=(\d+)")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reachable(gs, bound):
    # Simple coin reachability, independent of the graph's bitset index and
    # the evaluators' Apéry/bit-mask representations.
    result = [False] * (bound + 1)
    result[0] = True
    for n in range(1, bound + 1):
        result[n] = any(g <= n and result[n - g] for g in gs)
    return result


def canonical(gs):
    gs = sorted(set(gs))
    require(bool(gs) and all(type(g) is int and g > 1 for g in gs), "invalid generators")
    result = []
    for g in gs:
        if not reachable(result, g)[g]:
            result.append(g)
    return tuple(result)


def label(gs):
    return ",".join(map(str, canonical(gs)))


def gaps(gs):
    require(gcd(*gs) == 1, "gap enumeration requires gcd one")
    # m consecutive representable integers imply all following integers are
    # representable, since m is a generator. The bound is a resource guard,
    # never a mathematical cutoff accepted as evidence.
    values = [True]
    run = 0
    missing = []
    for n in range(1, 1000000):
        represented = any(g <= n and values[n - g] for g in gs)
        values.append(represented)
        run = run + 1 if represented else 0
        if not represented:
            missing.append(n)
        if run >= min(gs):
            return missing
    raise ValueError("gap enumeration resource limit reached")


def memory_limit():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))


def verify(data, native_check=None):
    require(data["schema"] == 1, "unsupported schema")
    facts = data["facts"]
    visited, active = set(), set()
    counts = Counter()
    theorem_leaves = []

    def visit(k):
        require(k in facts, f"missing fact {k}")
        require(k not in active, f"circular proof at {k}")
        if k in visited:
            return
        gs = tuple(map(int, k.split(",")))
        require(canonical(gs) == gs, f"noncanonical position {k}")
        active.add(k)
        fact = facts[k]
        kind = fact["kind"]
        outcome = fact["outcome"]
        require(outcome in ("P", "N"), f"invalid outcome at {k}")
        if kind == "finite-exact":
            finite_gaps = gaps(gs)
            require(fact["frobenius"] == max(finite_gaps), f"wrong Frobenius at {k}")
            winner = fact["winning_move"]
            require((outcome == "P") == (winner is None), f"inconsistent finite result at {k}")
            if winner is not None:
                require(winner > 1 and winner in finite_gaps, f"illegal finite reply at {k}")
            if native_check:
                native_check(gs, fact)
        elif kind == "winning-reply":
            move = fact["move"]
            require(type(move) is int and move > 1 and not reachable(gs, move)[move], f"illegal edge at {k}")
            dest = label((*gs, move))
            require(dest == fact["destination"], f"false semigroup identity at {k}")
            visit(dest)
            require(outcome == "N" and facts[dest]["outcome"] == "P", f"unsupported N at {k}")
        elif kind == "short-cover":
            require(gcd(*gs) == 2 and gs != (2,), f"not a short gcd-two position: {k}")
            half = tuple(g // 2 for g in gs)
            half_gaps = gaps(half)
            frob = max(half_gaps)
            bits = reachable(half, frob)
            require(all(bits[frob - m] for m in half_gaps if m < frob), f"half not quiet at {k}")
            require(fact["tail"] == "quiet-end-theorem" and fact["half_frobenius"] == frob,
                    f"invalid tail metadata at {k}")
            required_moves = sorted([2 * m for m in half_gaps] + [m for m in half_gaps if m > 1 and m % 2])
            rows = fact["obligations"]
            require(sorted(row["move"] for row in rows) == required_moves, f"incomplete cover at {k}")
            for row in rows:
                dest = label((*gs, row["move"]))
                require(dest == row["destination"], f"false child identity at {k}")
                visit(dest)
                require(facts[dest]["outcome"] == "N", f"unrefuted move at {k}")
            require(outcome == "P", f"invalid cover outcome at {k}")
        elif kind == "public-theorem":
            require(gs in PUBLIC_THEOREMS and outcome == "P", f"unsupported theorem at {k}")
            require(fact["source"] == "https://sicherman.net/sylver/ppos.html", "invalid theorem reference")
            theorem_leaves.append(k)
        else:
            raise ValueError(f"unknown evidence kind: {kind}")
        active.remove(k)
        visited.add(k)
        counts[kind] += 1

    root = label(data["root"])
    visit(root)
    require(facts[root]["outcome"] == "P", "root is not P")
    require(visited == set(facts), "unreachable facts in public certificate")
    return {"root": root, "outcome": "P", "facts": dict(counts),
            "published_P_dependencies": sorted(theorem_leaves)}


def check_correction():
    u, x, q = (16, 26, 88), (16, 26, 82, 88), (16, 26, 88, 98)
    require(canonical((*u, 82)) == x and canonical((*u, 98)) == q, "U children")
    require(canonical((*q, 82)) == x, "Q+82=X")
    require(canonical((8, 10, 22, 4)) == (4, 10), "counterexample identity")
    # A repeated full recurrence state certifies the infinite odd tail.
    # Merely inspecting the same number of odd moves would not suffice.
    report = analyze_odd_tail((8, 10, 22), 201)
    require(report.p_values == () and report.period_length == 8, "counterexample odd-tail proof")
    responses = {2: 3, 4: 6, 6: 4, 12: 14, 14: 12}
    require(sorted(responses) == [2 * m for m in gaps((4, 5, 11))], "counterexample complete even moves")
    for move, reply in responses.items():
        child = canonical((8, 10, 22, move))
        dest = canonical((*child, reply))
        require(dest in ((2, 3), (4, 6), (8, 10, 12, 14)), "counterexample even cover")
    require(canonical((4, 10, 6)) == (4, 6), "lower child is N via 6")
    require(not solve_position((2, 3)).is_winning, "terminal control")
    return {"Q_plus_82_equals_X": True, "absorption_counterexample": True,
            "counterexample_odd_period": report.period_length,
            "published_pairing_dependency": "8,10,12,14"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, default=HERE / "evidence/certificate.json")
    parser.add_argument("--structure-only", action="store_true",
                        help="audit coverage and identities without recomputing finite outcomes")
    parser.add_argument("--seconds", type=float, default=300, help="timeout per finite position")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.certificate.read_text())
    native_source = HERE / "sylver/native_solver.cpp"
    require(hashlib.sha256(native_source.read_bytes()).hexdigest() == data["native_source_sha256"],
            "native source hash mismatch")
    with tempfile.TemporaryDirectory(prefix="sylver-public-verify-") as directory:
        binary = Path(directory) / "native_solver"
        records = []
        if not args.structure_only:
            subprocess.run(["g++", "-std=c++20", "-O3", "-Wall", "-Wextra", "-pedantic",
                            "-DSYLVER_NATIVE_WORDS=8", str(native_source), "-o", str(binary)], check=True)

        def check(gs, fact):
            run = subprocess.run([str(binary), *map(str, gs)], capture_output=True, text=True,
                                 check=True, timeout=args.seconds, preexec_fn=memory_limit)
            match = ROW.fullmatch(run.stdout.strip())
            require(match is not None, f"invalid native output at {gs}")
            outcome, winner, frob, states = match.groups()
            require(outcome == fact["outcome"] and int(frob) == fact["frobenius"], f"finite mismatch at {gs}")
            require((None if winner == "none" else int(winner)) == fact["winning_move"], f"reply mismatch at {gs}")
            python_control = int(states) <= 10000
            if python_control:
                reference = solve_position(gs)
                require(reference.is_winning == (outcome == "N"), f"Python/native mismatch at {gs}")
            records.append({"position": list(gs), "outcome": outcome, "states": int(states),
                            "python_control": python_control})
            print("RECOMPUTED", label(gs), outcome, flush=True)

        summary = verify(data, None if args.structure_only else check)
        summary["finite_outcomes_recomputed"] = not args.structure_only
        summary["finite_replay"] = records
        summary["correction_controls"] = check_correction()
        if args.output:
            args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(json.dumps({k: v for k, v in summary.items() if k != "finite_replay"}, sort_keys=True))


if __name__ == "__main__":
    main()
