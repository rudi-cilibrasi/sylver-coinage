"""The even flank of X = {16,26,82,88}.

X is the boundary of the move-26 campaign: U={16,26,88} is N iff X is P
(RUN_MOVE_26_U_SUBTREE.txt).  X's odd replies are refuted through 407; its
finitely many even replies were never examined.  Any even child of X that
is a P-position proves X is N, and every refuted even child is a mandatory
ingredient of any future X-is-P certificate.  Both outcomes are progress.

No outcome is ever inferred from search time, a finite prefix, or a
heuristic: routing claims are verified by exact semigroup computation, and
scan outcomes come from the exact native recurrence.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import sys
from math import gcd
from pathlib import Path
from typing import Iterable

from sylver.parallel_solve import (
    RangeRow,
    ScanJob,
    cache_key,
    load_cache,
    run_jobs,
)
from sylver.short_certificates import (
    EXTERNAL_NODES,
    NODES,
    PUBLISHED_LONG_NODES,
    SHORT_NATIVE_FINITE_P_POSITIONS,
    legal_moves_at_gcd_two,
    minimal_generators,
)
from sylver.solver import FiniteSolver

X_BASE = (16, 26, 82, 88)

EXPECTED_EVEN_CHILDREN = (
    2, 4, 6, 8, 10, 12, 14, 18, 20, 22, 24, 28, 30, 34, 36, 38,
    40, 44, 46, 50, 54, 56, 60, 62, 66, 70, 72, 76, 86, 92, 102, 118,
)


def even_children(base: tuple[int, ...] = X_BASE) -> tuple[int, ...]:
    """Every legal even move of a gcd-two position (finite by g=2 theory)."""
    return legal_moves_at_gcd_two(base)


def known_p_semigroups() -> dict[tuple[int, ...], str]:
    """Minimal generating sets of every certified or published P-position."""
    table: dict[tuple[int, ...], str] = {(2, 3): "finite:{2,3}"}
    for node in NODES:
        table[node.generators] = f"node:{node.name}"
    for name, generators in EXTERNAL_NODES.items():
        table[minimal_generators(generators)] = f"pairing:{name}"
    for name, generators in PUBLISHED_LONG_NODES.items():
        table[minimal_generators(generators)] = f"published:{name}"
    for position in SHORT_NATIVE_FINITE_P_POSITIONS:
        table[minimal_generators(position)] = "native-finite"
    return table


@dataclasses.dataclass(frozen=True)
class ChildStatus:
    child: int
    status: str  # "refuted" or "open"
    reply: int | None = None
    mechanism: str = ""
    destination: tuple[int, ...] = ()


def route_children(
    cache: dict[str, bool],
    base: tuple[int, ...] = X_BASE,
    odd_reply_limit: int = 501,
) -> dict[int, ChildStatus]:
    """Refute children for free using audited data and certified nodes.

    Pass 1 recycles the exact cache and the certified table over odd
    replies; pass 2 does the same over the finitely many even replies.
    Every claim is an exact minimal-generator identity, never a pattern
    match.  Children no pass refutes are reported "open" for the scans.
    """
    p_table = known_p_semigroups()
    statuses: dict[int, ChildStatus] = {}
    for child in even_children(base):
        statuses[child] = _route_one_child(
            base, child, cache, p_table, odd_reply_limit
        )
    return statuses


def _route_one_child(
    base: tuple[int, ...],
    child: int,
    cache: dict[str, bool],
    p_table: dict[tuple[int, ...], str],
    odd_reply_limit: int,
) -> ChildStatus:
    child_generators = minimal_generators((*base, child))
    # Pass 1: odd replies.  Every odd integer is a legal move on an
    # all-even semigroup, and a destination already proved P refutes the
    # child outright.  This must run before any even-reply handling so the
    # degenerate child {2} (whose half <1> breaks gap enumeration) closes
    # here via the classic P-pair {2,3}.
    for reply in range(3, odd_reply_limit + 1, 2):
        destination = minimal_generators((*child_generators, reply))
        if destination in p_table:
            return ChildStatus(
                child, "refuted", reply, p_table[destination], destination
            )
        if cache.get(cache_key(destination)) is True:
            return ChildStatus(child, "refuted", reply, "cache", destination)
    # Pass 2: even replies (finitely many).
    for reply in even_children(child_generators):
        destination = minimal_generators((*child_generators, reply))
        if destination in p_table:
            return ChildStatus(
                child, "refuted", reply, p_table[destination], destination
            )
        if cache.get(cache_key(destination)) is True:
            return ChildStatus(child, "refuted", reply, "cache-even", destination)
    return ChildStatus(child, "open")


@dataclasses.dataclass(frozen=True)
class HalfClassification:
    child: int
    child_generators: tuple[int, ...]
    half: tuple[int, ...]
    quiet: bool
    half_frobenius: int
    exceptional_odds: tuple[int, ...]


def classify_half(
    child: int, base: tuple[int, ...] = X_BASE
) -> HalfClassification:
    """Quiet-ender check for one even child, verified before any pruning.

    Only when the half is a verified quiet ender does the Quiet End Theorem
    confine possible odd winners to the odd gaps of the half: an odd move
    inside the half's semigroup produces a quiet ender and loses.  For a
    non-quiet half no odd move may be pruned (the {10,16,24,28} precedent),
    so exceptional_odds is left empty and callers must scan unboundedly.
    """
    child_generators = minimal_generators((*base, child))
    if gcd(*child_generators) != 2:
        raise ValueError(f"child {child} does not have gcd two")
    half = tuple(value // 2 for value in child_generators)
    if half == (1,):
        raise ValueError(f"child {child} is the degenerate semigroup <2>")
    solver = FiniteSolver(half)
    quiet = solver.is_quiet_ender()
    exceptional = (
        tuple(m for m in solver.gaps() if m % 2 == 1 and m >= 3)
        if quiet
        else ()
    )
    return HalfClassification(
        child=child,
        child_generators=child_generators,
        half=half,
        quiet=quiet,
        half_frobenius=solver.frobenius,
        exceptional_odds=exceptional,
    )


def hint_pool(rows: Iterable[RangeRow], size: int = 8) -> tuple[int, ...]:
    """Most frequent recorded winners, deterministically ordered."""
    counts: dict[int, int] = {}
    for row in rows:
        if row.winning_move is not None:
            counts[row.winning_move] = counts.get(row.winning_move, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(winner for winner, _ in ranked[:size])


def build_scan_jobs(
    statuses: dict[int, ChildStatus],
    *,
    base: tuple[int, ...] = X_BASE,
    sortie_moves: int = 100,
    hints: tuple[int, ...] = (),
    timeout_seconds: float = 3600.0,
) -> list[ScanJob]:
    """One scan job per open child.

    Quiet children scan exactly their exceptional odds — if every one is N,
    the child is a P-candidate pending even-side certification.  Non-quiet
    children get a bounded sortie of the first `sortie_moves` odd replies;
    a sortie can refute a child but never certify it P.
    """
    jobs: list[ScanJob] = []
    for child in sorted(statuses):
        if statuses[child].status != "open":
            continue
        classification = classify_half(child, base)
        if classification.quiet:
            moves = classification.exceptional_odds
        else:
            moves = tuple(range(3, 3 + 2 * sortie_moves, 2))
        if not moves:
            continue
        jobs.append(
            ScanJob(
                base=classification.child_generators,
                moves=moves,
                hints=hints,
                timeout_seconds=timeout_seconds,
            )
        )
    return jobs


@dataclasses.dataclass(frozen=True)
class CampaignReport:
    statuses: dict[int, ChildStatus]
    p_candidates: tuple[int, ...]
    open_children: tuple[int, ...]
    rows_recorded: int
    rounds_run: int


def run_campaign(
    *,
    base: tuple[int, ...] = X_BASE,
    cache_path: Path,
    output_directory: Path,
    workers: int = 10,
    sortie_moves: int = 100,
    timeout_seconds: float = 3600.0,
    rounds: int = 3,
) -> CampaignReport:
    """Route, scan, and re-route until the flank stops moving.

    Every round merges completed scan rows into the flank cache, so later
    rounds route through earlier rounds' exact results.  Hints for round
    k+1 are the deterministic winner pool of rounds 1..k.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    flank_cache_path = output_directory / "x_even_flank.cache"
    ledger_path = output_directory / "x_even_flank_ledger.jsonl"
    build_directory = output_directory / "build"

    seed = load_cache(cache_path)
    all_rows: list[RangeRow] = []
    odd_clean: set[int] = set()
    statuses: dict[int, ChildStatus] = {}
    rounds_run = 0

    for _ in range(max(1, rounds)):
        rounds_run += 1
        combined = dict(seed)
        combined.update(load_cache(flank_cache_path))
        statuses = route_children(combined, base=base)
        open_now = [c for c, s in statuses.items() if s.status == "open"]
        # A quiet child whose full exceptional list is already N cannot be
        # refuted by more odd scanning; skip it (even-side work remains).
        to_scan = {c: statuses[c] for c in open_now if c not in odd_clean}
        if not to_scan:
            break
        jobs = build_scan_jobs(
            to_scan,
            base=base,
            sortie_moves=sortie_moves,
            hints=hint_pool(all_rows),
            timeout_seconds=timeout_seconds,
        )
        if not jobs:
            break
        results = run_jobs(
            jobs,
            cache_path=flank_cache_path,
            ledger_path=ledger_path,
            build_directory=build_directory,
            workers=workers,
        )
        new_rows = 0
        for result in results:
            all_rows.extend(result.rows)
            new_rows += len(result.rows)
            child = _child_of(result.job.base, base)
            classification = classify_half(child, base)
            if (
                classification.quiet
                and result.completed
                and all(row.outcome == "N" for row in result.rows)
                and {row.move for row in result.rows}
                == set(classification.exceptional_odds)
            ):
                odd_clean.add(child)
        if new_rows == 0:
            break

    combined = dict(seed)
    combined.update(load_cache(flank_cache_path))
    statuses = route_children(combined, base=base)
    p_candidates = tuple(
        sorted(c for c in odd_clean if statuses[c].status == "open")
    )
    open_children = tuple(
        sorted(
            c
            for c, s in statuses.items()
            if s.status == "open" and c not in p_candidates
        )
    )
    report = CampaignReport(
        statuses=statuses,
        p_candidates=p_candidates,
        open_children=open_children,
        rows_recorded=len(all_rows),
        rounds_run=rounds_run,
    )
    write_run_record(
        output_directory / "RUN_RECORD.txt",
        report,
        command_line=(
            f"base={','.join(map(str, base))} cache={cache_path}"
            f" workers={workers} sortie_moves={sortie_moves}"
            f" timeout={timeout_seconds} rounds={rounds}"
        ),
    )
    return report


def _child_of(job_base: tuple[int, ...], base: tuple[int, ...]) -> int:
    """Recover which even child a scan job belongs to."""
    for child in even_children(base):
        if minimal_generators((*base, child)) == job_base:
            return child
    raise ValueError(f"scan base {job_base} is not a child of {base}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_run_record(
    path: Path, report: CampaignReport, command_line: str
) -> None:
    module_dir = Path(__file__).resolve().parent
    lines = [
        "X even-flank campaign record",
        f"command: {command_line}",
        "",
        "source fingerprints (sha256):",
    ]
    for name in ("native_solver.cpp", "parallel_solve.py", "x_even_flank.py"):
        lines.append(f"  {_sha256(module_dir / name)}  {name}")
    lines += [
        "",
        f"rounds run: {report.rounds_run}",
        f"scan rows recorded: {report.rows_recorded}",
        "",
        "child statuses:",
    ]
    for child in sorted(report.statuses):
        status = report.statuses[child]
        if status.status == "refuted":
            destination = ",".join(map(str, status.destination))
            lines.append(
                f"  {child}: refuted by {status.reply}"
                f" via {status.mechanism} -> {{{destination}}}"
            )
        elif child in report.p_candidates:
            lines.append(
                f"  {child}: P-CANDIDATE (odd side clean;"
                " even-side certification required)"
            )
        else:
            lines.append(f"  {child}: open")
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--sortie-moves", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--base", type=str, default="16,26,82,88")
    arguments = parser.parse_args(argv)
    report = run_campaign(
        base=tuple(int(g) for g in arguments.base.split(",")),
        cache_path=arguments.cache,
        output_directory=arguments.output,
        workers=arguments.workers,
        sortie_moves=arguments.sortie_moves,
        timeout_seconds=arguments.timeout,
        rounds=arguments.rounds,
    )
    refuted = sum(1 for s in report.statuses.values() if s.status == "refuted")
    print(
        f"refuted {refuted}/{len(report.statuses)};"
        f" p_candidates={list(report.p_candidates)};"
        f" open={list(report.open_children)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
