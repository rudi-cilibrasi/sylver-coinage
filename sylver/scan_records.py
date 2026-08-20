"""Bank historical scan artifacts into the audited cache format.

The move-26 campaigns left exact scan outputs (`full_*.txt`,
`*_record.txt`, `x_sortie.txt`) and a JSONL ledger whose refutations
never entered the periodicity exact cache.  Each artifact row is an
exact native-recurrence outcome; importing it is recycling, not
recomputation.  Every text-record row is validated by recomputing the
child's Frobenius number against the claimed base — a row that does not
match its base is rejected loudly rather than banked wrongly.
"""

from __future__ import annotations

import json
from pathlib import Path

from sylver.parallel_solve import cache_key, parse_scan_output
from sylver.solver import frobenius_number, normalize_generators

# Text records and the base position their rows scan, reconstructed from
# the campaign run records and re-verified per row by Frobenius check.
HISTORICAL_RECORDS: dict[str, tuple[int, ...]] = {
    "full_38.txt": (16, 26, 38, 88),
    "full_70.txt": (16, 26, 70, 88),
    "full_82.txt": (16, 26, 82, 88),
    "full_98_lo.txt": (16, 26, 88, 98),
    "full_108.txt": (16, 26, 88, 108),
    "x_sortie.txt": (16, 26, 82, 88),
    "move26_odd_record.txt": (16, 26),
    "node88_odd_record.txt": (16, 26, 88),
    "nodeV_odd_record.txt": (16, 26, 36, 56),
}


def _record(outcomes: dict[str, bool], key: str, flag: bool) -> None:
    if outcomes.get(key, flag) != flag:
        raise ValueError(f"conflicting outcomes for {key}")
    outcomes[key] = flag


def outcomes_from_record(
    base: tuple[int, ...], path: Path
) -> dict[str, bool]:
    """Import a native scan output, validating every row's Frobenius."""
    outcomes: dict[str, bool] = {}
    for row in parse_scan_output(base, path.read_text()):
        child = normalize_generators(base + (row.move,))
        expected = frobenius_number(child)
        if expected != row.frobenius:
            raise ValueError(
                f"{path.name}: move {row.move} claims Frobenius"
                f" {row.frobenius} but {child} has {expected}"
            )
        _record(outcomes, cache_key(child), row.outcome == "P")
        if row.winning_move is not None:
            _record(
                outcomes,
                cache_key(base + (row.move, row.winning_move)),
                True,
            )
    return outcomes


def outcomes_from_ledger(path: Path) -> dict[str, bool]:
    """Import the campaign JSONL ledger (pos + [move, outcome, winner,
    frobenius, states] rows), with the same per-row Frobenius check."""
    outcomes: dict[str, bool] = {}
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            base = tuple(int(g) for g in entry["pos"])
            for move, outcome, winner, frobenius, _states in entry["rows"]:
                child = normalize_generators(base + (int(move),))
                expected = frobenius_number(child)
                if expected != int(frobenius):
                    raise ValueError(
                        f"{path.name}: {base} move {move} claims Frobenius"
                        f" {frobenius} but {child} has {expected}"
                    )
                _record(outcomes, cache_key(child), outcome == "P")
                if outcome == "N" and winner is not None:
                    _record(
                        outcomes,
                        cache_key(base + (int(move), int(winner))),
                        True,
                    )
    return outcomes


def all_historical_outcomes(directory: Path) -> dict[str, bool]:
    """Merge every artifact, cross-checking for conflicts."""
    outcomes: dict[str, bool] = {}
    for source in [outcomes_from_ledger(directory / "ledger.jsonl")] + [
        outcomes_from_record(base, directory / name)
        for name, base in HISTORICAL_RECORDS.items()
    ]:
        for key, flag in source.items():
            _record(outcomes, key, flag)
    return outcomes
