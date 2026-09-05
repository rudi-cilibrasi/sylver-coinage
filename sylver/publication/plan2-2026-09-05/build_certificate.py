"""Rebuild a shareable certificate using public code and fresh computation.

No campaign cache, imported claim, or private archive is read. Repository
response tables select candidate replies; their outcomes are checked anew.
Unknown even children are searched in ascending odd-reply order.
"""
import argparse
import hashlib
import json
import resource
import selectors
import subprocess
import time
from math import gcd
from pathlib import Path

from sylver.parallel_solve import compile_solver, parse_scan_output
from sylver.proof_graph import ProofGraph, key, profile
from sylver.reconcile_campaign import NATIVE_ROW
from sylver.short_certificates import NODES, minimal_generators
from sylver.solver import frobenius_number

ROOT = (16, 26, 54, 60, 62)


def memory_limit():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))


class Builder:
    def __init__(self, output, seconds):
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.build = output / "build"
        self.build.mkdir(exist_ok=True)
        self.seconds = seconds
        self.source_hash = hashlib.sha256(
            Path("sylver/native_solver.cpp").read_bytes()).hexdigest()
        self.hints = ProofGraph()
        self.hints.seed_repository()
        self.nodes = {key(n.generators): n for n in NODES}
        self.facts = {}
        self.active = set()
        path = output / "certificate.json"
        if path.exists():
            previous = json.loads(path.read_text())
            if previous["native_source_sha256"] != self.source_hash:
                raise ValueError("native source changed; use a fresh directory")
            self.facts = previous["facts"]

    def save(self):
        data = {"schema": 1, "root": list(ROOT),
                "native_source_sha256": self.source_hash,
                "provenance": "public repository tables and fresh native computations; no imported claims or caches",
                "facts": self.facts}
        tmp = self.output / "certificate.json.tmp"
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.output / "certificate.json")

    def finite(self, gs, expected):
        frob = frobenius_number(gs)
        words = next(w for w in (1, 2, 4, 8, 16) if frob < 64 * w)
        binary = compile_solver(words, self.build).resolve()
        start = time.monotonic()
        run = subprocess.run([str(binary), *map(str, gs)], text=True,
                             capture_output=True, check=True,
                             timeout=self.seconds, preexec_fn=memory_limit)
        match = NATIVE_ROW.fullmatch(run.stdout.strip())
        if not match:
            raise ValueError(run.stdout)
        result, winner, found_frob, states = match.groups()
        if result != expected or int(found_frob) != frob:
            raise ValueError(f"unexpected finite outcome: {gs}: {run.stdout}")
        return {"outcome": result, "kind": "finite-exact", "frobenius": frob,
                "winning_move": None if winner == "none" else int(winner),
                "states": int(states), "native_words": words,
                "elapsed_seconds": round(time.monotonic() - start, 6)}

    def find_odd_reply(self, gs):
        # Shared memo makes an ascending scan affordable. A finite P hit is
        # sufficient; a completed prefix without one never proves anything.
        moves = tuple(range(3, 302, 2))
        binary = compile_solver(8, self.build).resolve()
        command = [str(binary), "--odd-list", ",".join(map(str, moves)), *map(str, gs)]
        deadline = time.monotonic() + self.seconds
        log = self.output / ("scan-" + key(gs) + ".txt")
        with log.open("w") as handle, subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, preexec_fn=memory_limit) as proc:
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            try:
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline - time.monotonic())):
                        break
                    line = proc.stdout.readline()
                    if not line:
                        break
                    handle.write(line)
                    handle.flush()
                    rows = parse_scan_output(gs, line)
                    if len(rows) != 1:
                        raise ValueError(f"invalid scan row: {line}")
                    row = rows[0]
                    if row.move not in moves or row.frobenius != frobenius_number((*gs, row.move)):
                        raise ValueError(f"invalid scan arithmetic: {line}")
                    if row.outcome == "P":
                        print("FOUND", key(gs), row.move, flush=True)
                        return row.move
                raise RuntimeError(f"no completed P hit for {gs}; see {log.name}")
            finally:
                selector.close()
                if proc.poll() is None:
                    proc.kill()
                proc.wait()

    def prove(self, generators, expected):
        gs = minimal_generators(generators)
        k = key(gs)
        if k in self.facts:
            if self.facts[k]["outcome"] != expected:
                raise ValueError(f"outcome conflict at {k}")
            return k
        if k in self.active:
            raise ValueError(f"circular dependency at {k}")
        self.active.add(k)
        print("PROVE", expected, k, flush=True)
        if gcd(*gs) == 1:
            fact = self.finite(gs, expected)
        elif expected == "N":
            hint = self.hints.route(gs)
            if hint and hint["outcome"] == "N" and hint["evidence"]["kind"] == "winning-edge":
                move = hint["evidence"]["move"]
            else:
                move = self.find_odd_reply(gs)
            dest = self.prove((*gs, move), "P")
            fact = {"outcome": "N", "kind": "winning-reply", "move": move, "destination": dest}
        elif profile(gs)["complete_moves"]:
            info = profile(gs)
            responses = {m: r for m, r, _ in self.nodes[k].even_responses} if k in self.nodes else {}
            obligations = []
            for move in info["moves"]:
                child = minimal_generators((*gs, move))
                ck = key(child)
                if move in responses and ck not in self.facts:
                    reply = responses[move]
                    dest = self.prove((*child, reply), "P")
                    self.facts[ck] = {"outcome": "N", "kind": "winning-reply",
                                      "move": reply, "destination": dest}
                self.prove(child, "N")
                obligations.append({"move": move, "destination": ck})
            fact = {"outcome": "P", "kind": "short-cover", "half_frobenius": info["half_frobenius"],
                    "obligations": obligations, "tail": "quiet-end-theorem"}
        else:
            # Named, public external results are explicit trust dependencies.
            # They are not disguised as a finite scan or a fresh computation.
            allowed = {(8, 12), (8, 10, 22), (8, 12, 18, 22), (8, 10, 12, 14), (8, 12, 26, 30)}
            if gs not in allowed:
                raise ValueError(f"unsupported P leaf {gs}")
            fact = {"outcome": "P", "kind": "public-theorem",
                    "source": "https://sicherman.net/sylver/ppos.html"}
        self.facts[k] = fact
        self.active.remove(k)
        self.save()
        return k


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("rebuilt-evidence"))
    parser.add_argument("--seconds", type=float, default=300)
    args = parser.parse_args()
    builder = Builder(args.output, args.seconds)
    builder.prove(ROOT, "P")
    builder.save()
    print("CERTIFIED", key(ROOT), "P", len(builder.facts), "facts")


if __name__ == "__main__":
    main()
