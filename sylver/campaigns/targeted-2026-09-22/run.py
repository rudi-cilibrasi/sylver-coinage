#!/usr/bin/env python3
"""Bounded targeted evaluation on an isolated copy of the audited cache."""

import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache(path):
    result = {}
    for line in path.read_text().splitlines():
        k, v = line.split()
        if v not in ("0", "1") or result.get(k, v) != v:
            raise ValueError(f"bad or conflicting cache row: {line}")
        result[k] = v
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("target", type=int)
    parser.add_argument("generators", type=int, nargs="+")
    parser.add_argument("--seconds", type=float, default=90)
    parser.add_argument("--memory-gib", type=int, default=6)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--start", type=int)
    parser.add_argument("--stop-on-p", action="store_true")
    parser.add_argument("--full", action="store_true", help="run full periodicity rows instead of targeted queries")
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--add-cache", type=Path, action="append", default=[])
    args = parser.parse_args()
    if (args.seconds <= 0 or args.memory_gib <= 0 or args.threads not in range(1, 65)
            or not args.label or Path(args.label).name != args.label):
        parser.error("invalid resource limits or label")
    if (args.full and (args.start is not None or args.stop_on_p)
            or args.resume_checkpoint is not None and not args.full):
        parser.error("full mode and targeted range options are incompatible")
    run = HERE / args.label
    run.mkdir()  # Refuse to overwrite an earlier experiment.
    seed_path = ROOT / "sylver/move26_data/periodicity_x.cache"
    seed = cache(seed_path)
    sources = [{"path": str(seed_path.relative_to(ROOT)), "sha256": digest(seed_path)}]
    for path in args.add_cache:
        for k, v in cache(path).items():
            if seed.get(k, v) != v:
                raise ValueError(f"conflicting input caches at {k}")
            seed[k] = v
        sources.append({"path": str(path), "sha256": digest(path)})
    source = ROOT / "sylver/periodicity_engine.cpp"
    source_hash = digest(source)
    build = HERE / "build"
    build.mkdir(exist_ok=True)
    binary = build / f"engine-{source_hash[:16]}"
    if not binary.exists():
        subprocess.run(["g++", "-std=c++20", "-O3", "-Wall", "-Wextra",
                        "-pedantic", "-pthread", str(source), "-o", str(binary)], check=True)

    def cap():
        limit = args.memory_gib * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    with tempfile.TemporaryDirectory(prefix="sylver-target-") as directory:
        work = Path(directory) / "exact.cache"
        work.write_text("".join(f"{k} {v}\n" for k, v in sorted(seed.items())))
        command = [str(binary), str(work), str(args.target),
                   "--memory-report", "--exact-threads", str(args.threads),
                   *map(str, args.generators)]
        checkpoint = run / "build" / "rowstate"
        if args.full:
            checkpoint.parent.mkdir()
            if args.resume_checkpoint is not None:
                shutil.copyfile(args.resume_checkpoint, checkpoint)
            command += ["--checkpoint-file", str(checkpoint)]
        else:
            command += ["--target-only"]
        if args.start is not None:
            command += ["--target-start", str(args.start)]
        if args.stop_on_p:
            command.append("--stop-on-p")
        metadata = {"base": args.generators, "target": args.target,
                    "sources": sources, "engine_sha256": source_hash,
                    "seconds": args.seconds, "memory_gib": args.memory_gib,
                    "exact_threads": args.threads, "command": command}
        metadata.update(target_start=args.start, stop_on_p=args.stop_on_p)
        metadata["target_only"] = not args.full
        if args.resume_checkpoint is not None:
            metadata["resume_checkpoint"] = {"path": str(args.resume_checkpoint),
                                              "sha256": digest(args.resume_checkpoint)}
        (run / "inputs.json").write_text(json.dumps(metadata, indent=2) + "\n")
        with (run / "output.log").open("w") as log:
            start = time.monotonic()
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       preexec_fn=cap)
            print("TARGET-PROCESS", process.pid, "log", run / "output.log", flush=True)
            timed_out = forced_kill = False
            try:
                rc = process.wait(timeout=args.seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.send_signal(signal.SIGINT)
                try:
                    rc = process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    forced_kill = True
                    process.kill()
                    rc = process.wait()
            elapsed = time.monotonic() - start
        final = cache(work)
        if any(final.get(k) != v for k, v in seed.items()):
            raise ValueError("input outcomes changed or disappeared")
        added = {k: v for k, v in final.items() if k not in seed}
        (run / "added.cache").write_text(
            "".join(f"{k} {v}\n" for k, v in sorted(added.items())))
    receipt = {**metadata, "returncode": rc, "timed_out": timed_out,
               "forced_kill": forced_kill, "elapsed_seconds": elapsed,
               "added_exact_outcomes": len(added), "added_P": sum(v == "1" for v in added.values()),
               "log_sha256": digest(run / "output.log"),
               "delta_sha256": digest(run / "added.cache")}
    if args.full and checkpoint.exists():
        receipt["checkpoint"] = {"path": str(checkpoint), "sha256": digest(checkpoint),
                                 "bytes": checkpoint.stat().st_size}
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
