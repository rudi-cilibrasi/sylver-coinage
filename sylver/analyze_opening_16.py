#!/usr/bin/env python3
"""Inspect exceptional odd moves after an even response to opening 16.

For an even response ``m``, divide ``{16,m}`` by its gcd ``d``.  Except for
the trivial divisor cases, the reduced position is a coprime pair and hence a
quiet ender.  The Quiet End Theorem shows that an odd next move already in the
reduced semigroup produces another quiet ender, so it cannot be winning.  Only
the finitely many odd gaps of the reduced semigroup need exact evaluation.

This script searches that finite exceptional set.  It does not classify even
moves, and therefore does not by itself determine the outcome of ``{16,m}``.
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Sequence

from sylver.solver import FiniteSolver, solve_position


def exceptional_odd_wins(response: int) -> tuple[int, ...]:
    """Return odd moves that provably leave a finite P-position."""
    if response <= 1 or response % 2 or response % 16 == 0:
        raise ValueError("response must be an even legal move after 16")

    divisor = math.gcd(16, response)
    reduced = tuple(sorted({16 // divisor, response // divisor}))
    if 1 in reduced:
        # If response divides 16, the position reduces to the singleton {1}
        # after scaling.  This is one of the already-solved opening cases.
        return ()

    base = FiniteSolver(reduced)
    if not base.is_quiet_ender():
        raise AssertionError("a coprime two-generator position must be a quiet ender")

    wins: list[int] = []
    for move in base.legal_moves(base.initial_state):
        if move % 2 == 0:
            continue
        if not solve_position((16, response, move)).is_winning:
            wins.append(move)
    return tuple(wins)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="find exceptional odd winning moves after {16,m}"
    )
    parser.add_argument("response", metavar="M", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        wins = exceptional_odd_wins(args.response)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    rendered = ", ".join(str(move) for move in wins) if wins else "none"
    print(f"{{16, {args.response}}}: exceptional odd winning moves: {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
