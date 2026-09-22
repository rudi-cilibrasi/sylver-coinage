#!/usr/bin/env python3
"""Bounded experiment: reuse explicitly identified finite P facts in a memo.

Results depend on the supplied P cache. Requested roots are excluded from the
seed so this measures actual evaluation rather than cached-root lookup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE_HASH = "aded19fa091b57b6bb307c60824d44655a02353b6bc87c5b2ad0a996fda71c66"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("label")
    p.add_argument("positions", nargs="+", help="comma-separated gcd-one positions")
    p.add_argument("--cache", type=Path, action="append", default=[])
    p.add_argument("--seconds", type=float, default=120)
    p.add_argument("--memory-gib", type=int, default=6)
    p.add_argument("--words", type=int, default=5)
    args = p.parse_args()
    if (not args.label or Path(args.label).name != args.label
            or min(args.seconds, args.memory_gib, args.words) <= 0):
        p.error("invalid label or limits")
    source = ROOT / "sylver/native_solver.cpp"
    if digest(source) != BASE_HASH:
        raise ValueError("experimental patch requires the recorded native source")
    run = HERE / args.label
    run.mkdir()
    build = run / "build"
    build.mkdir()
    patched = build / "seeded.cpp"
    patched.write_bytes(source.read_bytes())
    patch = HERE / "pseed-solver.patch"
    subprocess.run(["patch", "--silent", str(patched)], input=patch.read_text(),
                   text=True, check=True)
    binary = build / "seeded"
    subprocess.run(["g++", "-std=c++20", "-O3", "-Wall", "-Wextra", "-pedantic",
                    f"-DSYLVER_NATIVE_WORDS={args.words}", str(patched),
                    "-o", str(binary)], check=True)
    caches = [ROOT / "sylver/move26_data/periodicity_x.cache", *args.cache]
    outcomes = {}
    for cache in caches:
        for line in cache.read_text().splitlines():
            k, v = line.split()
            if v not in ("0", "1") or outcomes.get(k, v) != v:
                raise ValueError("invalid or conflicting cache fact")
            outcomes[k] = v
    seeds = build / "p.cache"
    seeds.write_text(''.join(f"{k} 1\n" for k, v in sorted(outcomes.items())
                            if v == "1" and k not in args.positions))
    positions = run / "positions.txt"
    positions.write_text('\n'.join(args.positions) + '\n')
    command = [str(binary), "--p-cache", str(seeds), "--batch-file", str(positions)]
    metadata = {"sources": [{"path": str(c), "sha256": digest(c)} for c in caches],
                "base_source_sha256": BASE_HASH, "patch_sha256": digest(patch),
                "source_sha256": digest(patched), "native_words": args.words,
                "seed_sha256": digest(seeds), "excluded_seed_roots": args.positions,
                "positions_sha256": digest(positions), "command": command,
                "seconds": args.seconds, "memory_gib": args.memory_gib,
                "scope": "Memo seeded with inherited P facts; outcomes retain those dependencies."}
    (run / "inputs.json").write_text(json.dumps(metadata, indent=2) + '\n')

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (args.memory_gib * 1024**3,) * 2)

    start = time.monotonic()
    with (run / "stdout.txt").open('w') as out, (run / "stderr.txt").open('w') as err:
        proc = subprocess.Popen(command, stdout=out, stderr=err, preexec_fn=cap)
        print("SEEDED", args.label, "pid", proc.pid, flush=True)
        timed_out = False
        try:
            proc.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
    receipt = {**metadata, "returncode": proc.returncode, "timed_out": timed_out,
               "elapsed_seconds": time.monotonic() - start,
               "stdout_sha256": digest(run / "stdout.txt"),
               "stderr_sha256": digest(run / "stderr.txt")}
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + '\n')
    print((run / "stdout.txt").read_text(), end='', flush=True)


if __name__ == "__main__":
    main()
