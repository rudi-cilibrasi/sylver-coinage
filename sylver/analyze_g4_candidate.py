#!/usr/bin/env python3
"""Exactly inspect bounded odd children of a proposed even P-position.

The current target is ``{16,20,28}``, which the primary literature singles
out as a plausible gcd-four P-position.  Any odd move from an all-even
position makes the gcd one, so :mod:`sylver.solver` can determine that child
exactly.  This is only a bounded diagnostic: even moves and the unbounded odd
tail remain separate proof obligations.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import solve_position


@dataclass(frozen=True)
class OddChildResult:
    move: int
    response: int | None
    frobenius: int
    states_evaluated: int


def inspect_odd_children(
    generators: Iterable[int], bound: int
) -> tuple[OddChildResult, ...]:
    """Evaluate every legal odd move from ``generators`` through ``bound``."""

    position = minimal_generators(generators)
    if any(value % 2 for value in position):
        raise ValueError("the candidate position must be all even")
    if bound < 3:
        raise ValueError("bound must be at least 3")

    results: list[OddChildResult] = []
    for move in range(3, bound + 1, 2):
        if is_generated(position, move):
            continue
        solution = solve_position((*position, move))
        results.append(
            OddChildResult(
                move,
                solution.winning_move,
                solution.frobenius,
                solution.states_evaluated,
            )
        )
    return tuple(results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="exactly inspect bounded odd children of an even position"
    )
    parser.add_argument("bound", type=int)
    parser.add_argument("generators", metavar="N", type=int, nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        results = inspect_odd_children(args.generators, args.bound)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    for result in results:
        response = str(result.response) if result.response is not None else "P CHILD"
        print(
            f"move {result.move}: response {response}; "
            f"F={result.frobenius}; states={result.states_evaluated}"
        )
    refuted = sum(result.response is not None for result in results)
    print(f"refuted odd children: {refuted}/{len(results)} through {args.bound}")
    return 0 if refuted == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
