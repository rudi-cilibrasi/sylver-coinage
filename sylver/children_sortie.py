"""Head-on sorties against the open even children of {16,26}.

Any child {16,26,c} that is a P-position answers move 26 outright by the
reply c, without deciding X.  Every child refuted narrows the {16,26}-P
question.  Jobs scan only moves absent from the audited cache, in small
chunks so no shared solver memo can approach the historical 45+ GB
full-scan blowups, shallow chunks across all children first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sylver.parallel_solve import (
    ScanJob,
    cache_key,
    load_cache,
    merge_cache,
    run_jobs,
)
from sylver.short_certificates import is_generated, minimal_generators
from sylver.x_even_flank import route_children

BASE = (16, 26)


def uncached_odd_moves(
    child: int,
    cache: dict[str, bool],
    *,
    depth: int = 401,
) -> tuple[int, ...]:
    """Odd replies to {16,26,child} with no banked outcome, ascending."""
    child_generators = minimal_generators((*BASE, child))
    moves = []
    for move in range(3, depth + 1, 2):
        if is_generated(child_generators, move):
            continue
        if cache_key((*child_generators, move)) in cache:
            continue
        moves.append(move)
    return tuple(moves)


def build_chunked_jobs(
    children: list[int],
    cache: dict[str, bool],
    *,
    depth: int = 401,
    chunk: int = 30,
    timeout_seconds: float = 10800.0,
    memory_bytes: int = 10 * 1024**3,
) -> list[ScanJob]:
    """Depth-interleaved chunk jobs: all children's shallow work first."""
    per_child: dict[int, tuple[int, ...]] = {
        child: uncached_odd_moves(child, cache, depth=depth)
        for child in children
    }
    staged: list[tuple[int, int, ScanJob]] = []
    for child, moves in per_child.items():
        base = minimal_generators((*BASE, child))
        for start in range(0, len(moves), chunk):
            piece = moves[start : start + chunk]
            if not piece:
                continue
            staged.append(
                (
                    piece[0],
                    child,
                    ScanJob(
                        base=base,
                        moves=piece,
                        timeout_seconds=timeout_seconds,
                        memory_bytes=memory_bytes,
                    ),
                )
            )
    staged.sort(key=lambda item: (item[0], item[1]))
    return [job for _, _, job in staged]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--max-wide-workers", type=int, default=6)
    parser.add_argument("--depth", type=int, default=401)
    parser.add_argument("--chunk", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=10800.0)
    arguments = parser.parse_args(argv)

    cache = load_cache(arguments.cache)
    statuses = route_children(cache, base=BASE)
    children = sorted(
        c for c, s in statuses.items() if s.status == "open" and c != 88
    )
    print(f"open children (88 excluded, blocked on X): {children}")
    jobs = build_chunked_jobs(
        children,
        cache,
        depth=arguments.depth,
        chunk=arguments.chunk,
        timeout_seconds=arguments.timeout,
    )
    total_moves = sum(len(job.moves) for job in jobs)
    print(f"jobs: {len(jobs)} chunks covering {total_moves} uncached moves")
    arguments.output.mkdir(parents=True, exist_ok=True)
    results = run_jobs(
        jobs,
        cache_path=arguments.output / "children_sortie.cache",
        ledger_path=arguments.output / "children_sortie_ledger.jsonl",
        build_directory=arguments.output / "build",
        workers=arguments.workers,
        max_wide_workers=arguments.max_wide_workers,
    )
    p_rows = [
        row
        for result in results
        for row in result.rows
        if row.outcome == "P"
    ]
    incomplete = sum(1 for result in results if not result.completed)
    print(f"scan rows: {sum(len(r.rows) for r in results)};"
          f" P rows: {len(p_rows)}; incomplete chunks: {incomplete}")
    for row in p_rows:
        print(f"  REFUTED child of {row.base} by {row.move}")
    combined = dict(cache)
    combined.update(load_cache(arguments.output / "children_sortie.cache"))
    after = route_children(combined, base=BASE)
    still_open = sorted(
        c for c, s in after.items() if s.status == "open" and c != 88
    )
    print(f"still open after sortie: {still_open}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
