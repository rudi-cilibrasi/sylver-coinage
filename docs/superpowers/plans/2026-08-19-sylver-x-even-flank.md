# Sylver X Even Flank + Parallel Solve Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parallel exact-solve service (§1 of the spec) and run the bounded even-flank sortie on X={16,26,82,88} (§2), reaching the spec's decision gate: either some even child of X is P (⟹ X is N ⟹ 88 answers move 26) or all 32 are N (banked as the even half of a future X-is-P certificate).

**Architecture:** Process-level parallelism — a Python orchestrator drives N=10 worker subprocesses, each running the existing single-threaded native C++ solver on one whole scan job. The solver core's search loop is untouched; it gains only a root-level hint pass (outcome-invariant reordering) and an explicit odd-move-list mode. All results flow through the audited exact-cache row format (`<comma-joined minimal generators> <0|1>`, 1 = P) with atomic temp-file+rename writes and conflict-detection on merge.

**Tech Stack:** C++20 (g++, `-O3 -Wall -Wextra -pedantic`, warning-clean), Python 3 stdlib only (unittest, dataclasses, concurrent.futures, subprocess, hashlib), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-19-sylver-move26-hybrid-design.md` (§1 and §2; §3/§4 are a follow-up plan triggered only by the all-N outcome).

## Global Constraints

- **Exact-outcome discipline (verbatim from spec):** "No outcome is ever inferred from search time, a finite prefix, or a heuristic."
- C++ builds must be warning-clean under `g++ -std=c++20 -O3 -Wall -Wextra -pedantic`; wide builds use `-DSYLVER_NATIVE_WORDS=16` (F≤1023) or `32` (F≤2047).
- Cache row format: `<comma-joined minimal generators> <0|1>` where `1` means P. Writes are temp-file + `os.replace`. Merge conflicts (same key, different outcome) abort with an exception — never silently overwrite.
- Default workers: 10 (12 cores, 2 reserved). Jobs needing words>8 run under a 3-slot semaphore. Per-worker address-space limit 12 GiB via `ulimit -v` (bash wrapper — `preexec_fn` is not thread-safe).
- Hints are **static per job** (computed deterministically before the run from prior audited data). No dynamic cross-worker hint pooling — it would make winner selection scheduling-dependent and break parallel-vs-serial cache equality.
- Existing audited artifacts (`sylver/RUN_*.txt`, `sylver/move26_data/*`) are read-only inputs. New outputs go to new files. The only exception is Task 7's final reviewed merge into `periodicity_x.cache`, which records the file's SHA-256 before and after.
- The Quiet End Theorem's gap-restriction for odd moves is applied **only after** `FiniteSolver(half).is_quiet_ender()` returns True (the `{10,16,24,28}` cautionary precedent).
- Commit after every task, directly on `master`, sentence-case imperative subject (repo style), body optional, trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Run targeted tests per task; run the full sylver test files (`python -m unittest tests.test_sylver_solver tests.test_sylver_native_solver tests.test_sylver_periodicity tests.test_sylver_parallel_solve tests.test_sylver_x_even_flank -v`) before the Task 6 and Task 7 commits.

## File Structure

- Modify: `sylver/native_solver.cpp` — add `--hints` (root-level candidate ordering) and `--odd-list` (explicit move list) modes; flush scan rows per-line.
- Create: `sylver/parallel_solve.py` — cache/ledger I/O, output parsing, binary compilation, job runner (the §1 service).
- Create: `sylver/x_even_flank.py` — child enumeration, symbolic router, half classification, scan-job builder, campaign runner + run-record writer (the §2 sortie).
- Create: `tests/test_sylver_parallel_solve.py`, `tests/test_sylver_x_even_flank.py`; extend `tests/test_sylver_native_solver.py`.
- Campaign outputs (Task 7): `sylver/move26_data/x_even_flank.cache`, `sylver/move26_data/x_even_flank_ledger.jsonl`, `sylver/RUN_X_EVEN_FLANK.txt`.
- NOT touched: `sylver/periodicity_engine.cpp`, `sylver/solver.py`, `sylver/short_certificates.py` (consumed read-only).

## Key repo facts for implementers (verified 2026-08-19)

- `sylver/solver.py`: `solve_position(generators) -> Solution` (fields `generators, frobenius, winning_move, states_evaluated`, property `is_winning`); `FiniteSolver(gens)` with `.frobenius`, `.gaps()` (returns `(1, *legal_moves)`), `.is_quiet_ender()`; `frobenius_number(gens)`, `normalize_generators(gens)`.
- `sylver/short_certificates.py`: `minimal_generators(iterable) -> tuple`, `is_generated(gens, value) -> bool`, `legal_moves_at_gcd_two(gens) -> tuple` (raises unless gcd is exactly 2), `NODES: tuple[ShortNode]` (fields `name, generators, even_responses`), `EXTERNAL_NODES: dict[str, tuple]`, `PUBLISHED_LONG_NODES: dict[str, tuple]`, `SHORT_NATIVE_FINITE_P_POSITIONS: set[tuple]`.
- Native CLI today: `native_solver GEN...` → `P|N winning_move=<m|none> frobenius=<f> states=<n>`; `native_solver --odd-range START END GEN...` → per-move rows `move=<m> P|N winning_move=<m|none> frobenius=<f> cumulative_states=<n>`. Word width fixed at compile time: `kMaximumFrobenius = 64*words - 1`.
- The audited cache `sylver/move26_data/periodicity_x.cache` has 216,251 rows of form `16,26,... 0|1`. Keys are minimal-generator sets. 1 = P.
- Known identities used in tests: `98 = 16+82` so `minimal_generators((16,26,82,88,98)) == (16,26,82,88)`; `26+56=82` and `16+36+36=88` so `minimal_generators((16,26,82,88,36,56)) == (16,26,36,56)` (= certified node V).
- X's 32 even children (2× gaps of `<8,13,41,44>`): `2,4,6,8,10,12,14,18,20,22,24,28,30,34,36,38,40,44,46,50,54,56,60,62,66,70,72,76,86,92,102,118`.

---

### Task 1: `--hints` and `--odd-list` in the native solver

**Files:**
- Modify: `sylver/native_solver.cpp`
- Test: `tests/test_sylver_native_solver.py` (append to existing class; `cls.binary` is compiled in `setUpClass`)

**Interfaces:**
- Consumes: existing `Solver`, `parse_generators`, `frobenius_number` in `native_solver.cpp`.
- Produces (CLI contract for Task 3):
  - `native_solver [--hints H1,H2,...] GEN...` — single-position mode, output format unchanged.
  - `native_solver [--hints H1,H2,...] --odd-list M1,M2,... GEN...` — scans exactly the listed odd moves (each ≥3, odd) as replies to the base; per-move output rows identical in format to `--odd-range`, flushed per line.
  - `native_solver [--hints H1,H2,...] --odd-range START END GEN...` — unchanged semantics, rows now flushed per line.
  - With hints, the reported `winning_move` may be any valid winner, not necessarily the least. Outcomes never change.

- [ ] **Step 1: Write the failing tests**

Append to the existing test class in `tests/test_sylver_native_solver.py` (it already imports `solve_position` and compiles `cls.binary`):

```python
    def run_native(self, *arguments: str) -> str:
        return subprocess.run(
            [str(self.binary), *arguments],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_hints_do_not_change_single_position_outcomes(self) -> None:
        for generators in [(16, 6, 3), (16, 6, 7), (16, 10, 9), (16, 18, 5), (4, 6, 9)]:
            reference = solve_position(generators)
            plain = self.run_native(*map(str, generators))
            hinted = self.run_native("--hints", "9,5,3,201", *map(str, generators))
            expected = "N" if reference.is_winning else "P"
            self.assertEqual(plain.split()[0], expected)
            self.assertEqual(hinted.split()[0], expected)
            winner = hinted.split()[1].removeprefix("winning_move=")
            if winner != "none":
                # Any reported winner must reach an exact P-position.
                child = solve_position((*generators, int(winner)))
                self.assertFalse(child.is_winning)

    def test_odd_list_matches_odd_range(self) -> None:
        range_output = self.run_native("--odd-range", "3", "13", "4", "6")
        list_output = self.run_native("--odd-list", "3,5,7,9,11,13", "4", "6")
        self.assertEqual(range_output, list_output)

    def test_odd_list_supports_gaps_in_the_move_list(self) -> None:
        output = self.run_native("--odd-list", "3,7,13", "4", "6")
        moves = [line.split()[0] for line in output.strip().splitlines()]
        self.assertEqual(moves, ["move=3", "move=7", "move=13"])

    def test_hinted_odd_range_outcomes_match_plain(self) -> None:
        plain = self.run_native("--odd-range", "3", "13", "6", "16")
        hinted = self.run_native("--hints", "7", "--odd-range", "3", "13", "6", "16")
        plain_outcomes = [line.split()[1] for line in plain.strip().splitlines()]
        hinted_outcomes = [line.split()[1] for line in hinted.strip().splitlines()]
        self.assertEqual(plain_outcomes, hinted_outcomes)

    def test_odd_list_rejects_even_or_small_moves(self) -> None:
        for bad in ("4", "1", "2,5"):
            result = subprocess.run(
                [str(self.binary), "--odd-list", bad, "4", "6"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_native_solver -v 2>&1 | tail -20`
Expected: the five new tests FAIL (`--hints`/`--odd-list` are reported as unusable generators → `CalledProcessError`), all pre-existing tests still PASS.

- [ ] **Step 3: Implement in `native_solver.cpp`**

3a. In the anonymous namespace, after `parse_generators`, add:

```cpp
[[nodiscard]] std::vector<int> parse_move_list(const std::string& text) {
    std::vector<int> moves;
    std::size_t begin = 0;
    while (begin <= text.size()) {
        std::size_t comma = text.find(',', begin);
        if (comma == std::string::npos) {
            comma = text.size();
        }
        const long value = std::stol(text.substr(begin, comma - begin));
        if (value < 2 || value > std::numeric_limits<int>::max()) {
            throw std::invalid_argument("listed moves must be integers greater than one");
        }
        moves.push_back(static_cast<int>(value));
        begin = comma + 1;
    }
    return moves;
}
```

3b. In `class Solver`, change the two public solve entry points to accept hints (default empty keeps every existing call site unchanged):

```cpp
    [[nodiscard]] int solve(const std::vector<int>& hints = {}) {
        return winning_move_hinted(initial_, hints);
    }
    [[nodiscard]] int solve_after_adjoining(int move, const std::vector<int>& hints = {}) {
        return winning_move_hinted(adjoin(initial_, move), hints);
    }
```

3c. In the private section of `Solver`, add above `winning_move`:

```cpp
    // Hints reorder only the root-level search.  Any winning move is a valid
    // N-certificate, so a hint that wins is returned immediately; otherwise
    // the unmodified exhaustive loop decides the position.  Outcomes cannot
    // change, only the order in which root children are explored.
    [[nodiscard]] int winning_move_hinted(const State& root, const std::vector<int>& hints) {
        if (const auto found = memo_.find(root); found != memo_.end()) {
            return found->second;
        }
        for (const int hint : hints) {
            if (hint < 2 || hint > frobenius_ || root.test(hint)) {
                continue;
            }
            if (winning_move(adjoin(root, hint)) == 0) {
                memo_.emplace(root, static_cast<std::uint16_t>(hint));
                return hint;
            }
        }
        return winning_move(root);
    }
```

3d. In the anonymous namespace, after `parse_generators`, add the shared scan driver (DRY: both list and range modes use it). Note `std::endl` per row — a timed-out worker must not lose finished rows to block buffering:

```cpp
void run_move_scan(
    const std::vector<int>& base,
    const std::vector<int>& moves,
    const std::vector<int>& hints
) {
    int bound = 0;
    for (const int move : moves) {
        std::vector<int> child = base;
        child.push_back(move);
        std::sort(child.begin(), child.end());
        if (std::accumulate(
                child.begin() + 1,
                child.end(),
                child.front(),
                [](int left, int right) { return std::gcd(left, right); }
            ) != 1) {
            throw std::invalid_argument("every scanned child must have gcd one");
        }
        bound = std::max(bound, frobenius_number(child));
    }
    if (bound > kMaximumFrobenius) {
        throw std::invalid_argument(
            "scan Frobenius bound exceeds native limit " +
            std::to_string(kMaximumFrobenius)
        );
    }
    Solver solver(base, bound);
    for (const int move : moves) {
        std::vector<int> child = base;
        child.push_back(move);
        std::sort(child.begin(), child.end());
        const int actual_frobenius = frobenius_number(child);
        const int response = solver.solve_after_adjoining(move, hints);
        std::cout << "move=" << move << ' '
                  << (response == 0 ? "P" : "N") << " winning_move=";
        if (response == 0) {
            std::cout << "none";
        } else {
            std::cout << response;
        }
        std::cout << " frobenius=" << actual_frobenius
                  << " cumulative_states=" << solver.states_evaluated()
                  << std::endl;
    }
}
```

3e. Rewrite `main` to strip an optional `--hints` prefix, add the `--odd-list` branch, and route `--odd-range` through `run_move_scan`:

```cpp
int main(int argc, char** argv) {
    try {
        std::vector<int> hints;
        if (argc >= 3 && std::string(argv[1]) == "--hints") {
            hints = parse_move_list(argv[2]);
            argv += 2;
            argc -= 2;
        }
        if (argc >= 2 && std::string(argv[1]) == "--odd-list") {
            if (argc < 4) {
                throw std::invalid_argument(
                    "odd-list mode requires MOVES and base generators"
                );
            }
            const std::vector<int> moves = parse_move_list(argv[2]);
            for (const int move : moves) {
                if (move < 3 || move % 2 == 0) {
                    throw std::invalid_argument(
                        "odd-list moves must be odd and at least 3"
                    );
                }
            }
            const std::vector<int> base = parse_generators(argc, argv, 3, false);
            run_move_scan(base, moves, hints);
            return EXIT_SUCCESS;
        }
        if (argc >= 2 && std::string(argv[1]) == "--odd-range") {
            if (argc < 6) {
                throw std::invalid_argument(
                    "odd-range mode requires START END and base generators"
                );
            }
            const int start = std::stoi(argv[2]);
            const int end = std::stoi(argv[3]);
            if (start < 3 || start > end || start % 2 == 0 || end % 2 == 0) {
                throw std::invalid_argument("odd range must have odd endpoints >= 3");
            }
            const std::vector<int> base = parse_generators(argc, argv, 4, false);
            std::vector<int> moves;
            for (int move = start; move <= end; move += 2) {
                moves.push_back(move);
            }
            run_move_scan(base, moves, hints);
            return EXIT_SUCCESS;
        }

        const std::vector<int> generators = parse_generators(argc, argv, 1, true);
        const int frobenius = frobenius_number(generators);
        if (frobenius > kMaximumFrobenius) {
            throw std::invalid_argument(
                "Frobenius number exceeds native limit " +
                std::to_string(kMaximumFrobenius)
            );
        }
        Solver solver(generators, frobenius);
        const int move = solver.solve(hints);
        std::cout << (move == 0 ? "P" : "N") << " winning_move=";
        if (move == 0) {
            std::cout << "none";
        } else {
            std::cout << move;
        }
        std::cout << " frobenius=" << frobenius
                  << " states=" << solver.states_evaluated() << '\n';
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "native_solver: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
```

Delete the old inline `--odd-range` loop body (it is fully replaced by `run_move_scan`). The `--odd-range` gcd error message changes from "every odd-range child must have gcd one" to "every scanned child must have gcd one" — nothing depends on the old text.

- [ ] **Step 4: Compile standalone and run the tests**

Run: `g++ -std=c++20 -O3 -Wall -Wextra -pedantic sylver/native_solver.cpp -o /tmp/claude-1001/-home-ruclaw-src-conway/b7a578fd-c176-441c-850b-e4de050179de/scratchpad/ns_check 2>&1 | head`
Expected: no output (warning-clean).
Run: `python -m unittest tests.test_sylver_native_solver -v 2>&1 | tail -20`
Expected: ALL tests PASS (new five + all pre-existing, which recompile the binary from the modified source).

- [ ] **Step 5: Commit**

```bash
git add sylver/native_solver.cpp tests/test_sylver_native_solver.py
git commit -m "Add root-level hints and explicit odd-list scans to the native solver

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: cache and output primitives in `parallel_solve.py`

**Files:**
- Create: `sylver/parallel_solve.py`
- Test: `tests/test_sylver_parallel_solve.py`

**Interfaces:**
- Consumes: `sylver.short_certificates.minimal_generators`, `sylver.solver.frobenius_number`, `sylver.solver.normalize_generators`.
- Produces (used by Tasks 3–6):
  - `cache_key(generators: Iterable[int]) -> str` — comma-joined minimal generators.
  - `load_cache(path: Path) -> dict[str, bool]` — raises `ValueError` on malformed or conflicting rows.
  - `write_cache(path: Path, outcomes: dict[str, bool]) -> None` — sorted rows, atomic replace.
  - `merge_cache(path: Path, new_outcomes: dict[str, bool]) -> int` — returns number added; raises `ValueError` on conflict.
  - `RangeRow(base: tuple, move: int, outcome: str, winning_move: int | None, frobenius: int)` frozen dataclass.
  - `parse_scan_output(base: tuple, text: str) -> list[RangeRow]` — complete rows only; partial trailing lines ignored.
  - `rows_to_outcomes(rows: Iterable[RangeRow]) -> dict[str, bool]` — child key → outcome, plus each N-row's winning destination as P (mirrors the periodicity engine's base-record import semantics).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sylver_parallel_solve.py`:

```python
import tempfile
import unittest
from pathlib import Path

from sylver.parallel_solve import (
    RangeRow,
    cache_key,
    load_cache,
    merge_cache,
    parse_scan_output,
    rows_to_outcomes,
    write_cache,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_CACHE = ROOT / "sylver" / "move26_data" / "periodicity_x.cache"


class CacheKeyTests(unittest.TestCase):
    def test_key_reduces_to_minimal_generators(self) -> None:
        self.assertEqual(cache_key((16, 26, 82, 88, 98)), "16,26,82,88")
        self.assertEqual(cache_key((16, 26, 82, 88)), "16,26,82,88")

    def test_key_agrees_with_the_audited_cache_sample(self) -> None:
        # The engine's C++ minimal_generators wrote these keys; the Python
        # helper must reproduce every sampled key verbatim.
        with REAL_CACHE.open() as handle:
            for _, line in zip(range(50), handle):
                key = line.split()[0]
                generators = tuple(int(g) for g in key.split(","))
                self.assertEqual(cache_key(generators), key)


class CacheIoTests(unittest.TestCase):
    def test_write_load_roundtrip_and_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.cache"
            write_cache(path, {"4,7": True, "3,4": False})
            self.assertEqual(load_cache(path), {"4,7": True, "3,4": False})
            added = merge_cache(path, {"4,7": True, "2,3": True})
            self.assertEqual(added, 1)
            self.assertEqual(
                load_cache(path), {"4,7": True, "3,4": False, "2,3": True}
            )

    def test_merge_conflict_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.cache"
            write_cache(path, {"4,7": True})
            with self.assertRaises(ValueError):
                merge_cache(path, {"4,7": False})

    def test_load_rejects_malformed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.cache"
            path.write_text("4,7 2\n")
            with self.assertRaises(ValueError):
                load_cache(path)


class ScanOutputTests(unittest.TestCase):
    def test_parse_ignores_partial_trailing_line(self) -> None:
        text = (
            "move=3 N winning_move=4 frobenius=5 cumulative_states=10\n"
            "move=5 P winning_move=none frobenius=7 cumulative_states=25\n"
            "move=7 N winn"
        )
        rows = parse_scan_output((4, 6), text)
        self.assertEqual(
            rows,
            [
                RangeRow((4, 6), 3, "N", 4, 5),
                RangeRow((4, 6), 5, "P", None, 7),
            ],
        )

    def test_rows_to_outcomes_records_child_and_destination(self) -> None:
        rows = [
            RangeRow((4, 6), 3, "N", 4, 5),
            RangeRow((4, 6), 5, "P", None, 7),
        ]
        outcomes = rows_to_outcomes(rows)
        self.assertEqual(outcomes[cache_key((4, 6, 3))], False)
        self.assertEqual(outcomes[cache_key((4, 6, 5))], True)
        # The N-row's winning destination {4,6,3,4}={3,4} is a P-position.
        self.assertEqual(outcomes[cache_key((3, 4, 6))], True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_parallel_solve -v 2>&1 | tail -5`
Expected: FAIL with `ModuleNotFoundError: No module named 'sylver.parallel_solve'`.

- [ ] **Step 3: Implement the primitives**

Create `sylver/parallel_solve.py`:

```python
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
```

(`json`, `shlex`, `shutil`, `threading`, `ThreadPoolExecutor`, `subprocess`, `frobenius_number`, `normalize_generators`, `Sequence` are consumed by Task 3 in this same module; keeping the imports here avoids a churn commit.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_sylver_parallel_solve -v 2>&1 | tail -12`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sylver/parallel_solve.py tests/test_sylver_parallel_solve.py
git commit -m "Add audited cache and scan-output primitives for parallel solving

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: the job runner

**Files:**
- Modify: `sylver/parallel_solve.py`
- Test: `tests/test_sylver_parallel_solve.py`

**Interfaces:**
- Consumes: Task 2 primitives; Task 1 CLI contract.
- Produces (used by Tasks 5–6):
  - `ScanJob(base: tuple[int, ...], moves: tuple[int, ...], hints: tuple[int, ...] = (), timeout_seconds: float = 3600.0, memory_bytes: int = 12 * 1024**3)` frozen dataclass.
  - `required_words(job: ScanJob) -> int` — 8, 16, or 32; raises `ValueError` beyond F=2047.
  - `compile_solver(words: int, directory: Path) -> Path` — cached compile of the width variant.
  - `JobResult(job: ScanJob, rows: tuple[RangeRow, ...], completed: bool)` frozen dataclass.
  - `run_jobs(jobs: Sequence[ScanJob], *, cache_path: Path, ledger_path: Path, build_directory: Path, workers: int = 10, max_wide_workers: int = 3) -> list[JobResult]` — results ordered like `jobs`; cache and ledger updated incrementally under a lock.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sylver_parallel_solve.py`:

```python
from sylver.parallel_solve import (  # noqa: E402  (append to the import block)
    JobResult,
    ScanJob,
    compile_solver,
    required_words,
    run_jobs,
)
from sylver.solver import solve_position  # noqa: E402


class JobRunnerTests(unittest.TestCase):
    def test_required_words_matches_frobenius_bound(self) -> None:
        small = ScanJob(base=(4, 6), moves=(3, 5, 7, 9, 11, 13))
        self.assertEqual(required_words(small), 8)

    def test_parallel_matches_serial_and_reference(self) -> None:
        jobs = [
            ScanJob(base=(4, 6), moves=(3, 5, 7, 9, 11, 13)),
            ScanJob(base=(6, 16), moves=(3, 5, 7, 9), hints=(7,)),
        ]
        results_by_mode = {}
        caches = {}
        for label, workers in (("serial", 1), ("parallel", 4)):
            with tempfile.TemporaryDirectory() as directory:
                base_dir = Path(directory)
                results = run_jobs(
                    jobs,
                    cache_path=base_dir / "flank.cache",
                    ledger_path=base_dir / "ledger.jsonl",
                    build_directory=base_dir,
                    workers=workers,
                )
                results_by_mode[label] = results
                caches[label] = (base_dir / "flank.cache").read_text()
                ledger_lines = (
                    (base_dir / "ledger.jsonl").read_text().strip().splitlines()
                )
                self.assertEqual(len(ledger_lines), 10)  # 6 + 4 scan rows
        self.assertEqual(caches["serial"], caches["parallel"])
        for results in results_by_mode.values():
            self.assertTrue(all(result.completed for result in results))
            for result in results:
                for row in result.rows:
                    reference = solve_position(row.base + (row.move,))
                    self.assertEqual(row.outcome == "N", reference.is_winning)

    def test_timeout_returns_partial_result_without_raising(self) -> None:
        job = ScanJob(base=(16, 22), moves=(3, 5, 7, 9, 11), timeout_seconds=0.01)
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            results = run_jobs(
                [job],
                cache_path=base_dir / "flank.cache",
                ledger_path=base_dir / "ledger.jsonl",
                build_directory=base_dir,
                workers=1,
            )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].completed)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_parallel_solve -v 2>&1 | tail -8`
Expected: the three new tests FAIL with `ImportError` (names not yet defined); Task 2 tests still PASS.

- [ ] **Step 3: Implement the runner**

Append to `sylver/parallel_solve.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_sylver_parallel_solve -v 2>&1 | tail -12`
Expected: all 10 tests PASS (the parallel/serial case compiles the binary twice into temp dirs; allow ~30s).

- [ ] **Step 5: Commit**

```bash
git add sylver/parallel_solve.py tests/test_sylver_parallel_solve.py
git commit -m "Run native scan jobs across worker processes with audited persistence

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: child enumeration and the symbolic router

**Files:**
- Create: `sylver/x_even_flank.py`
- Test: `tests/test_sylver_x_even_flank.py`

**Interfaces:**
- Consumes: `legal_moves_at_gcd_two`, `minimal_generators`, `NODES`, `EXTERNAL_NODES`, `PUBLISHED_LONG_NODES`, `SHORT_NATIVE_FINITE_P_POSITIONS` from `sylver.short_certificates`; `cache_key`, `load_cache` from `sylver.parallel_solve`.
- Produces (used by Tasks 5–6):
  - `X_BASE = (16, 26, 82, 88)`; `EXPECTED_EVEN_CHILDREN` (the 32-tuple).
  - `even_children(base: tuple[int, ...] = X_BASE) -> tuple[int, ...]`.
  - `known_p_semigroups() -> dict[tuple[int, ...], str]` — minimal-generator tuple → mechanism label.
  - `ChildStatus(child: int, status: str, reply: int | None = None, mechanism: str = "", destination: tuple[int, ...] = ())` frozen dataclass; `status` is `"refuted"` or `"open"`.
  - `route_children(cache: dict[str, bool], base: tuple[int, ...] = X_BASE, odd_reply_limit: int = 501) -> dict[int, ChildStatus]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sylver_x_even_flank.py`:

```python
import unittest
from pathlib import Path

from sylver.parallel_solve import cache_key, load_cache
from sylver.x_even_flank import (
    EXPECTED_EVEN_CHILDREN,
    X_BASE,
    even_children,
    known_p_semigroups,
    route_children,
)

ROOT = Path(__file__).resolve().parents[1]
REAL_CACHE = ROOT / "sylver" / "move26_data" / "periodicity_x.cache"


class EnumerationTests(unittest.TestCase):
    def test_x_has_exactly_the_32_expected_even_children(self) -> None:
        self.assertEqual(even_children(), EXPECTED_EVEN_CHILDREN)
        self.assertEqual(len(EXPECTED_EVEN_CHILDREN), 32)

    def test_p0_has_the_eleven_even_moves_from_the_research_log(self) -> None:
        # RESEARCH.md Attempt 2: {12,16,22} has "eleven even moves".
        self.assertEqual(len(even_children((12, 16, 22))), 11)


class RouterTests(unittest.TestCase):
    def test_known_p_semigroups_contains_node_v_and_the_classic_pair(self) -> None:
        table = known_p_semigroups()
        self.assertEqual(table[(16, 26, 36, 56)], "node:V")
        self.assertIn((2, 3), table)

    def test_child_two_routes_to_the_classic_p_pair(self) -> None:
        statuses = route_children({})
        self.assertEqual(statuses[2].status, "refuted")
        self.assertEqual(statuses[2].reply, 3)
        self.assertEqual(statuses[2].destination, (2, 3))

    def test_children_36_and_56_route_into_node_v(self) -> None:
        # 26+56=82 and 16+36+36=88 collapse the destination onto V exactly.
        statuses = route_children({})
        for child, reply in ((36, 56), (56, 36)):
            self.assertEqual(statuses[child].status, "refuted")
            self.assertEqual(statuses[child].reply, reply)
            self.assertEqual(statuses[child].mechanism, "node:V")
            self.assertEqual(statuses[child].destination, (16, 26, 36, 56))

    def test_synthetic_cache_entry_refutes_a_child_via_pass_one(self) -> None:
        fake_cache = {cache_key((16, 26, 82, 88, 4, 7)): True}
        statuses = route_children(fake_cache)
        self.assertEqual(statuses[4].status, "refuted")
        self.assertEqual(statuses[4].reply, 7)
        self.assertEqual(statuses[4].mechanism, "cache")

    def test_real_cache_routing_report(self) -> None:
        statuses = route_children(load_cache(REAL_CACHE))
        refuted = [c for c, s in statuses.items() if s.status == "refuted"]
        self.assertIn(2, refuted)
        self.assertIn(36, refuted)
        self.assertIn(56, refuted)
        # Informational: how much the 216K-row investment recycles for free.
        print(
            f"\n[router] refuted {len(refuted)}/32 children:"
            f" {sorted(refuted)}"
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -5`
Expected: FAIL with `ModuleNotFoundError: No module named 'sylver.x_even_flank'`.

- [ ] **Step 3: Implement enumeration and router**

Create `sylver/x_even_flank.py`:

```python
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

import dataclasses

from sylver.parallel_solve import cache_key
from sylver.short_certificates import (
    EXTERNAL_NODES,
    NODES,
    PUBLISHED_LONG_NODES,
    SHORT_NATIVE_FINITE_P_POSITIONS,
    legal_moves_at_gcd_two,
    minimal_generators,
)

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -15`
Expected: all 6 tests PASS. Note the `[router]` line — record how many of the 32 children the audited cache refutes for free (children 2, 36, 56 at minimum).

- [ ] **Step 5: Commit**

```bash
git add sylver/x_even_flank.py tests/test_sylver_x_even_flank.py
git commit -m "Enumerate and symbolically route the 32 even children of X

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: half classification and scan-job construction

**Files:**
- Modify: `sylver/x_even_flank.py`
- Test: `tests/test_sylver_x_even_flank.py`

**Interfaces:**
- Consumes: Task 4 names; `FiniteSolver` from `sylver.solver`; `ScanJob` from `sylver.parallel_solve`.
- Produces (used by Task 6):
  - `HalfClassification(child: int, child_generators: tuple, half: tuple, quiet: bool, half_frobenius: int, exceptional_odds: tuple[int, ...])` frozen dataclass.
  - `classify_half(child: int, base: tuple[int, ...] = X_BASE) -> HalfClassification` — raises `ValueError` on gcd≠2 or the degenerate half `(1,)`.
  - `build_scan_jobs(statuses: dict[int, ChildStatus], *, base=X_BASE, sortie_moves: int = 100, hints: tuple[int, ...] = (), timeout_seconds: float = 3600.0) -> list[ScanJob]`.
  - `hint_pool(rows: Iterable[RangeRow], size: int = 8) -> tuple[int, ...]` — winners by descending frequency, ties by ascending value (deterministic).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sylver_x_even_flank.py`:

```python
from sylver.parallel_solve import RangeRow  # noqa: E402
from sylver.solver import FiniteSolver  # noqa: E402
from sylver.x_even_flank import (  # noqa: E402
    ChildStatus,
    build_scan_jobs,
    classify_half,
    hint_pool,
)


class HalfClassificationTests(unittest.TestCase):
    def test_x_half_is_not_a_quiet_ender(self) -> None:
        # Regression-locks the documented claim: <8,13,41,44> has a second
        # end, which is why X is long and the Quiet End Theorem gives no
        # odd-tail closure for X itself.
        self.assertFalse(FiniteSolver((8, 13, 41, 44)).is_quiet_ender())

    def test_quiet_child_of_p0_lists_exact_exceptional_odds(self) -> None:
        # {12,16,22} child 4 -> {4,22} (12=4*3, 16=4*4), half <2,11>, a
        # coprime pair, hence quiet, with odd gaps 3,5,7,9.
        classification = classify_half(4, base=(12, 16, 22))
        self.assertEqual(classification.child_generators, (4, 22))
        self.assertEqual(classification.half, (2, 11))
        self.assertTrue(classification.quiet)
        self.assertEqual(classification.exceptional_odds, (3, 5, 7, 9))

    def test_nonquiet_child_reports_no_exceptional_closure(self) -> None:
        for child in EXPECTED_EVEN_CHILDREN:
            classification = classify_half(child)
            if not classification.quiet:
                self.assertEqual(classification.exceptional_odds, ())

    def test_degenerate_child_two_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            classify_half(2)


class ScanJobBuilderTests(unittest.TestCase):
    def test_quiet_children_scan_their_exceptional_odds_only(self) -> None:
        statuses = {4: ChildStatus(4, "open"), 2: ChildStatus(2, "refuted", 3)}
        jobs = build_scan_jobs(statuses, base=(12, 16, 22))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].base, (4, 22))
        self.assertEqual(jobs[0].moves, (3, 5, 7, 9))

    def test_nonquiet_children_get_a_bounded_sortie(self) -> None:
        nonquiet = [
            child
            for child in EXPECTED_EVEN_CHILDREN
            if child != 2 and not classify_half(child).quiet
        ]
        if not nonquiet:
            self.skipTest("every X child half is quiet")
        child = nonquiet[0]
        statuses = {child: ChildStatus(child, "open")}
        jobs = build_scan_jobs(statuses, sortie_moves=10)
        self.assertEqual(jobs[0].moves, tuple(range(3, 23, 2)))

    def test_hint_pool_is_deterministic(self) -> None:
        rows = [
            RangeRow((4, 22), 3, "N", 9, 25),
            RangeRow((4, 22), 5, "N", 9, 25),
            RangeRow((4, 22), 7, "N", 3, 25),
        ]
        self.assertEqual(hint_pool(rows), (9, 3))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -8`
Expected: new tests FAIL with `ImportError`; Task 4 tests PASS.

- [ ] **Step 3: Implement**

Append to `sylver/x_even_flank.py` (extend the import block with `from math import gcd`, `from typing import Iterable`, `from sylver.parallel_solve import RangeRow, ScanJob`, `from sylver.solver import FiniteSolver`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -16`
Expected: all 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sylver/x_even_flank.py tests/test_sylver_x_even_flank.py
git commit -m "Classify child halves and build guarded scan jobs for the flank

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: campaign runner, report, and run-record writer

**Files:**
- Modify: `sylver/x_even_flank.py`
- Test: `tests/test_sylver_x_even_flank.py`

**Interfaces:**
- Consumes: everything above; `hashlib`, `argparse`, `json` from stdlib; `load_cache`, `merge_cache`, `run_jobs`, `JobResult` from `sylver.parallel_solve`.
- Produces:
  - `CampaignReport(statuses: dict[int, ChildStatus], p_candidates: tuple[int, ...], open_children: tuple[int, ...], rows_recorded: int, rounds_run: int)` frozen dataclass. A **p_candidate** is a quiet child whose every exceptional odd came back N — the odd side is clean; only even-side certification separates it from proving X is N. An open child is neither refuted nor a p_candidate.
  - `run_campaign(*, base=X_BASE, cache_path: Path, output_directory: Path, workers: int = 10, sortie_moves: int = 100, timeout_seconds: float = 3600.0, rounds: int = 3) -> CampaignReport`.
  - `write_run_record(path: Path, report: CampaignReport, command_line: str) -> None` — includes SHA-256 fingerprints of `native_solver.cpp`, `parallel_solve.py`, `x_even_flank.py`, and the input cache.
  - CLI: `python -m sylver.x_even_flank --cache PATH --output DIR [--workers N] [--sortie-moves N] [--timeout SECONDS] [--rounds N] [--base G,G,...]`.

- [ ] **Step 1: Write the failing test (mini-campaign on the certified P-node {12,16,22})**

Append to `tests/test_sylver_x_even_flank.py`:

```python
import tempfile  # noqa: E402

from sylver.x_even_flank import run_campaign  # noqa: E402


class MiniCampaignTests(unittest.TestCase):
    def test_p0_mini_campaign_pipeline(self) -> None:
        # {12,16,22} is the certified P-position P0, so every one of its 11
        # even children is N.  The pipeline must refute most of them and
        # must certify none as P.  Children whose only winning replies are
        # even (no odd refutation exists) may surface as p_candidates;
        # that is the correct verdict of an odd-side-only scan.
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            report = run_campaign(
                base=(12, 16, 22),
                cache_path=base_dir / "seed.cache",  # empty seed
                output_directory=base_dir / "out",
                workers=2,
                sortie_moves=20,
                timeout_seconds=120.0,
                rounds=2,
            )
        self.assertEqual(len(report.statuses), 11)
        refuted = [
            c for c, s in report.statuses.items() if s.status == "refuted"
        ]
        self.assertIn(2, refuted)   # reply 3 -> {2,3}
        self.assertIn(4, refuted)   # reply 6 -> node C={4,6}
        self.assertGreaterEqual(len(refuted), 8)
        for child in report.p_candidates:
            self.assertNotIn(child, refuted)
        self.assertEqual(
            sorted(refuted) + sorted(report.p_candidates)
            + sorted(report.open_children),
            sorted(report.statuses),
        )

    def test_run_record_contains_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base_dir = Path(directory)
            run_campaign(
                base=(12, 16, 22),
                cache_path=base_dir / "seed.cache",
                output_directory=base_dir / "out",
                workers=2,
                sortie_moves=5,
                timeout_seconds=60.0,
                rounds=1,
            )
            record = (base_dir / "out" / "RUN_RECORD.txt").read_text()
        self.assertIn("native_solver.cpp", record)
        self.assertIn("sha256", record.lower())
        self.assertIn("base=12,16,22", record)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -6`
Expected: FAIL with `ImportError: cannot import name 'run_campaign'`.

- [ ] **Step 3: Implement the runner**

Append to `sylver/x_even_flank.py` (extend imports: `import argparse`, `import hashlib`, `import sys`, `from pathlib import Path`, and `from sylver.parallel_solve import JobResult, load_cache, merge_cache, run_jobs`):

```python
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
    quiet_children: set[int] = set()
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
            if classification.quiet:
                quiet_children.add(child)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_sylver_x_even_flank -v 2>&1 | tail -20`
Expected: all 15 tests PASS. The mini-campaign compiles a binary and runs real scans over `{12,16,22}`'s children — allow ~60s.

- [ ] **Step 5: Run the full sylver suite**

Run: `python -m unittest tests.test_sylver_solver tests.test_sylver_native_solver tests.test_sylver_periodicity tests.test_sylver_parallel_solve tests.test_sylver_x_even_flank 2>&1 | tail -5`
Expected: OK (no failures, no errors).

- [ ] **Step 6: Commit**

```bash
git add sylver/x_even_flank.py tests/test_sylver_x_even_flank.py
git commit -m "Drive the even-flank campaign end to end with audited records

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: execute the real sortie and evaluate the decision gate

This task is a campaign run, not code. Its deliverables are audited artifacts plus updated dashboards.

**Files:**
- Create: `sylver/move26_data/x_even_flank.cache`, `sylver/move26_data/x_even_flank_ledger.jsonl`, `sylver/RUN_X_EVEN_FLANK.txt` (copied from the output directory's RUN_RECORD.txt, extended with the wave narrative).
- Modify: `sylver/RESEARCH.md` (Attempt 20), `STATUS.md`, `QUEUE.md`.
- Memory: update `sylver-move-26-frontier.md` after the gate.

- [ ] **Step 1: Wave 1 — router + quiet children + first sorties (hours)**

```bash
cd /home/ruclaw/src/conway
nohup python -m sylver.x_even_flank \
  --cache sylver/move26_data/periodicity_x.cache \
  --output sylver/move26_data/x_even_flank_run \
  --workers 10 --sortie-moves 100 --timeout 3600 --rounds 3 \
  > sylver/move26_data/x_even_flank_run.log 2>&1 &
```

Monitor with `tail -f sylver/move26_data/x_even_flank_run.log`. Expected duration: minutes for routing, then up to ~13 concurrent scans of an hour each per round.

- [ ] **Step 2: Wave 2 — escalate survivors**

For children still open after wave 1, rerun with deeper sorties and the accumulated ledger's hint pool (the runner does this automatically across rounds; a second invocation with `--sortie-moves 300 --timeout 14400` continues from the merged flank cache). Budget rule from the spec: 60 CPU-minutes per child batch by default, escalated deliberately, never silently.

- [ ] **Step 3: Evaluate the decision gate**

Three possible worlds; do exactly one:

**(a) Some child is proved P** (a quiet child's exceptional odds all N *and* its even side certified — see below — or a scan finds a P row directly for a child, i.e. some `{X,c,m}` destination equals a child position... note: only a completed quiet child or an exhaustive even+odd closure proves P).
For a p_candidate: run the even-side certification recursively —
`python -m sylver.x_even_flank --base <child_generators> --cache sylver/move26_data/periodicity_x.cache --output sylver/move26_data/flank_<child>` — every even grandchild must be refuted, plus the exceptional odds already N. If it closes: **X is N** (the child is a P destination for X's even move c).
Then, per the spec's decision gate: certify `U={16,26,88}` as a P-node in `short_certificates.py` with explicit N-witnesses for all 38 children — 36 already recorded in `RUN_MOVE_26_U_SUBTREE.txt`, child 82 (=X) N via the new P-witness, and child 98 (`{16,26,88,98}`) by its own concretely verified refutation (re-derive; do NOT cite the biconditional prose). Add the new P-position(s) to the node graph, run `verify_published_short_certificates`, extend `OPENING_16_EVEN_RESPONSES` with `(26, 88, "U")`, write RESEARCH.md Attempt 20 declaring **move 26 is answered by 88**, refresh STATUS.md and QUEUE.md, run the full test suite, commit.

**(b) All 32 children refuted (all N).** Bank the result: copy the flank cache rows into `sylver/move26_data/periodicity_x.cache` via `merge_cache` (record the cache's SHA-256 before and after in RUN_X_EVEN_FLANK.txt). Write RESEARCH.md Attempt 20: the even flank of X is closed N; X's classification now rests solely on the odd tail ≥409. Refresh dashboards. Commit. Then brainstorm/plan the follow-up: spec §3 (engine parallel fallbacks + hints + v2 checkpoint) and §4 (row-409 resume).

**(c) Mixed after escalation** (some children open, none P): write RESEARCH.md Attempt 20 with the exact frontier per child, bank all completed rows as in (b), refresh dashboards, commit, and proceed to the §3/§4 follow-up plan — the engine campaign and remaining flank scans can share future compute.

- [ ] **Step 4: Full verification before the final commit**

Run: `python -m unittest discover -s tests 2>&1 | tail -3` (the full 204+ test suite)
Run: `git diff --check`
Expected: OK; no whitespace errors.

- [ ] **Step 5: Final commit + memory update**

```bash
git add sylver/RUN_X_EVEN_FLANK.txt sylver/move26_data/x_even_flank.cache \
        sylver/move26_data/x_even_flank_ledger.jsonl sylver/RESEARCH.md \
        STATUS.md QUEUE.md
git commit -m "<outcome-specific subject per the gate branch>

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Update the memory file `sylver-move-26-frontier.md` with the gate outcome (one paragraph, pointing at RUN_X_EVEN_FLANK.txt).

---

## Plan Self-Review (completed)

- **Spec coverage:** §1 orchestrator → Tasks 2–3; §1 hints → Task 1; §1 TT-deferral → honored (no TT task; profiling note lives in the §3/§4 follow-up); §2 router → Task 4; §2 quiet-ender discipline → Task 5; §2 scans/budgets → Tasks 5–7; §2 decision gate incl. child-98 re-verification → Task 7; hint-invariance test → Task 1; parallel-vs-serial cache equality → Task 3. §3/§4 are explicitly a follow-up plan triggered by gate outcomes (b)/(c).
- **Placeholder scan:** Task 7 Step 3(a)'s certification is necessarily parameterized by the discovered witness; every mechanical step there names its exact function, file, and table. No TBDs remain.
- **Type consistency:** `ScanJob`/`RangeRow`/`JobResult` signatures match across Tasks 3–6; `ChildStatus` fields match between Tasks 4 and 6; `cache_key` used uniformly.
