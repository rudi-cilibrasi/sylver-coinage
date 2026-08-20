"""Parallel exact-solve service over the native Sylver evaluator.

Process-level parallelism: each worker runs the single-threaded native
solver on one whole scan job.  Every result flows through the audited
exact-cache row format (``<comma-joined minimal generators> <0|1>``, 1 = P)
with atomic writes and conflict detection.  No outcome is ever inferred
from search time, a finite prefix, or a heuristic.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Sequence

from sylver.short_certificates import minimal_generators
from sylver.solver import frobenius_number, normalize_generators

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sylver" / "native_solver.cpp"

_SCAN_ROW = re.compile(
    r"^move=(\d+) ([PN]) winning_move=(none|\d+)"
    r" frobenius=(\d+) cumulative_states=(\d+)$"
)


def cache_key(generators: Iterable[int]) -> str:
    """Comma-joined minimal generating set, the audited cache key format."""
    return ",".join(str(g) for g in minimal_generators(generators))


def load_cache(path: Path) -> dict[str, bool]:
    outcomes: dict[str, bool] = {}
    if not path.exists():
        return outcomes
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            key, _, value = line.rpartition(" ")
            if not key or value not in {"0", "1"}:
                raise ValueError(f"malformed cache row: {line!r}")
            flag = value == "1"
            if outcomes.get(key, flag) != flag:
                raise ValueError(f"conflicting cache rows for {key}")
            outcomes[key] = flag
    return outcomes


def write_cache(path: Path, outcomes: dict[str, bool]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as handle:
        for key in sorted(outcomes):
            handle.write(f"{key} {1 if outcomes[key] else 0}\n")
    os.replace(temporary, path)


def merge_cache(path: Path, new_outcomes: dict[str, bool]) -> int:
    existing = load_cache(path)
    added = 0
    for key, flag in new_outcomes.items():
        if key in existing:
            if existing[key] != flag:
                raise ValueError(f"cache conflict for {key}")
            continue
        existing[key] = flag
        added += 1
    write_cache(path, existing)
    return added


@dataclasses.dataclass(frozen=True)
class RangeRow:
    base: tuple[int, ...]
    move: int
    outcome: str
    winning_move: int | None
    frobenius: int


def parse_scan_output(base: tuple[int, ...], text: str) -> list[RangeRow]:
    rows: list[RangeRow] = []
    for line in text.splitlines():
        match = _SCAN_ROW.match(line.strip())
        if match is None:
            continue
        winner = match.group(3)
        rows.append(
            RangeRow(
                base=base,
                move=int(match.group(1)),
                outcome=match.group(2),
                winning_move=None if winner == "none" else int(winner),
                frobenius=int(match.group(4)),
            )
        )
    return rows


def rows_to_outcomes(rows: Iterable[RangeRow]) -> dict[str, bool]:
    """Cache entries implied by scan rows.

    An N row records its child as N and its winning destination as P,
    mirroring the periodicity engine's base-record import semantics.
    """
    outcomes: dict[str, bool] = {}

    def record(key: str, flag: bool) -> None:
        if outcomes.get(key, flag) != flag:
            raise ValueError(f"conflicting outcomes for {key}")
        outcomes[key] = flag

    for row in rows:
        record(cache_key(row.base + (row.move,)), row.outcome == "P")
        if row.winning_move is not None:
            record(cache_key(row.base + (row.move, row.winning_move)), True)
    return outcomes


@dataclasses.dataclass(frozen=True)
class ScanJob:
    """One native-solver invocation: scan explicit odd replies to a base."""

    base: tuple[int, ...]
    moves: tuple[int, ...]
    hints: tuple[int, ...] = ()
    timeout_seconds: float = 3600.0
    memory_bytes: int = 12 * 1024**3


@dataclasses.dataclass(frozen=True)
class JobResult:
    job: ScanJob
    rows: tuple[RangeRow, ...]
    completed: bool


def required_words(job: ScanJob) -> int:
    bound = max(
        frobenius_number(normalize_generators(job.base + (move,)))
        for move in job.moves
    )
    for words in (8, 16, 32):
        if bound <= 64 * words - 1:
            return words
    raise ValueError(f"scan Frobenius bound {bound} exceeds the 32-word build")


def compile_solver(words: int, directory: Path) -> Path:
    binary = directory / f"native_solver_w{words}"
    if binary.exists():
        return binary
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is required for the parallel solve service")
    subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-O3",
            "-Wall",
            "-Wextra",
            "-pedantic",
            f"-DSYLVER_NATIVE_WORDS={words}",
            str(SOURCE),
            "-o",
            str(binary),
        ],
        check=True,
        cwd=ROOT,
    )
    return binary


def _run_one(job: ScanJob, binary: Path) -> JobResult:
    command = [str(binary)]
    if job.hints:
        command += ["--hints", ",".join(str(h) for h in job.hints)]
    command += ["--odd-list", ",".join(str(m) for m in job.moves)]
    command += [str(g) for g in job.base]
    kilobytes = job.memory_bytes // 1024
    wrapped = [
        "bash",
        "-c",
        f"ulimit -v {kilobytes} && exec {shlex.join(command)}",
    ]
    process = subprocess.Popen(
        wrapped,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, _ = process.communicate(timeout=job.timeout_seconds)
        completed = process.returncode == 0
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, _ = process.communicate()
        completed = False
    rows = parse_scan_output(job.base, stdout or "")
    return JobResult(job=job, rows=tuple(rows), completed=completed)


def run_jobs(
    jobs: Sequence[ScanJob],
    *,
    cache_path: Path,
    ledger_path: Path,
    build_directory: Path,
    workers: int = 10,
    max_wide_workers: int = 3,
) -> list[JobResult]:
    """Run jobs concurrently; persist every completed row immediately.

    The cache contents are deterministic regardless of scheduling because
    outcomes are order-independent facts and conflicting rows abort.
    """
    build_directory.mkdir(parents=True, exist_ok=True)
    widths = [required_words(job) for job in jobs]
    binaries = {words: compile_solver(words, build_directory) for words in set(widths)}
    wide_slots = threading.Semaphore(max_wide_workers)
    io_lock = threading.Lock()

    def execute(index: int) -> JobResult:
        job = jobs[index]
        words = widths[index]
        if words > 8:
            wide_slots.acquire()
        try:
            result = _run_one(job, binaries[words])
        finally:
            if words > 8:
                wide_slots.release()
        with io_lock:
            merge_cache(cache_path, rows_to_outcomes(result.rows))
            with ledger_path.open("a") as handle:
                for row in result.rows:
                    handle.write(
                        json.dumps(
                            {
                                "base": list(row.base),
                                "move": row.move,
                                "outcome": row.outcome,
                                "winning_move": row.winning_move,
                                "frobenius": row.frobenius,
                                "job_completed": result.completed,
                            }
                        )
                        + "\n"
                    )
        return result

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(execute, range(len(jobs))))
