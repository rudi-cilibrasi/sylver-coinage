import tempfile
import unittest
from pathlib import Path

from sylver.parallel_solve import (
    RangeRow,
    ScanJob,
    cache_key,
    load_cache,
    merge_cache,
    parse_scan_output,
    required_words,
    rows_to_outcomes,
    run_jobs,
    write_cache,
)
from sylver.solver import solve_position

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
            "move=3 N winning_move=2 frobenius=5 cumulative_states=10\n"
            "move=5 N winning_move=7 frobenius=7 cumulative_states=25\n"
            "move=7 N winn"
        )
        rows = parse_scan_output((4, 6), text)
        self.assertEqual(
            rows,
            [
                RangeRow((4, 6), 3, "N", 2, 5),
                RangeRow((4, 6), 5, "N", 7, 7),
            ],
        )

    def test_rows_to_outcomes_records_child_and_destination(self) -> None:
        # Real values: {4,6,3}={3,4} is N (2 wins, reaching {2,3});
        # {4,6,5}={4,5,6} is N (7 wins, reaching the P-position {4,5,6,7}).
        rows = [
            RangeRow((4, 6), 3, "N", 2, 5),
            RangeRow((4, 6), 5, "N", 7, 7),
        ]
        outcomes = rows_to_outcomes(rows)
        self.assertEqual(outcomes[cache_key((4, 6, 3))], False)
        self.assertEqual(outcomes[cache_key((4, 6, 5))], False)
        self.assertEqual(outcomes[cache_key((2, 3))], True)
        self.assertEqual(outcomes[cache_key((4, 5, 6, 7))], True)


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
        job = ScanJob(
            base=(16, 26), moves=(21, 23, 25), timeout_seconds=0.05
        )
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


if __name__ == "__main__":
    unittest.main()
