import tempfile
import unittest
from pathlib import Path

from sylver.parallel_solve import cache_key
from sylver.scan_records import (
    HISTORICAL_RECORDS,
    outcomes_from_ledger,
    outcomes_from_record,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sylver" / "move26_data"


class RecordImportTests(unittest.TestCase):
    def test_record_rows_validate_frobenius_against_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.txt"
            # {4,6,3}={3,4} has Frobenius 5; a wrong claim must be rejected.
            path.write_text(
                "move=3 N winning_move=2 frobenius=5 cumulative_states=10\n"
            )
            outcomes = outcomes_from_record((4, 6), path)
            self.assertEqual(outcomes[cache_key((4, 6, 3))], False)
            self.assertEqual(outcomes[cache_key((2, 3))], True)
            path.write_text(
                "move=3 N winning_move=2 frobenius=99 cumulative_states=10\n"
            )
            with self.assertRaises(ValueError):
                outcomes_from_record((4, 6), path)

    def test_ledger_rows_import_with_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(
                '{"pos": [4, 6], "lo": 3, "hi": 5,'
                ' "rows": [[3, "N", 2, 5, 10], [5, "N", 7, 7, 25]]}\n'
            )
            outcomes = outcomes_from_ledger(path)
            self.assertEqual(outcomes[cache_key((4, 6, 3))], False)
            self.assertEqual(outcomes[cache_key((4, 6, 5))], False)
            self.assertEqual(outcomes[cache_key((2, 3))], True)
            self.assertEqual(outcomes[cache_key((4, 5, 6, 7))], True)

    def test_real_artifacts_import_without_conflict(self) -> None:
        total: dict[str, bool] = {}
        conflicts = 0
        ledger = outcomes_from_ledger(DATA / "ledger.jsonl")
        sources = [("ledger", ledger)]
        for name, base in HISTORICAL_RECORDS.items():
            sources.append((name, outcomes_from_record(base, DATA / name)))
        for name, outcomes in sources:
            for key, flag in outcomes.items():
                if total.get(key, flag) != flag:
                    conflicts += 1
                total[key] = flag
        self.assertEqual(conflicts, 0)
        self.assertGreater(len(total), 1500)
        print(f"\n[records] {len(total)} historical outcomes banked")


class ChildrenSortieBuilderTests(unittest.TestCase):
    def test_uncached_moves_exclude_banked_and_generated(self) -> None:
        from sylver.children_sortie import uncached_odd_moves

        cache = {cache_key((16, 26, 60, 3)): False}
        moves = uncached_odd_moves(60, cache, depth=15)
        self.assertNotIn(3, moves)          # banked
        self.assertEqual(moves, (5, 7, 9, 11, 13, 15))

    def test_chunked_jobs_are_depth_interleaved(self) -> None:
        from sylver.children_sortie import build_chunked_jobs

        jobs = build_chunked_jobs([60, 70], {}, depth=41, chunk=5)
        self.assertTrue(all(len(job.moves) <= 5 for job in jobs))
        # Both children's shallow chunks precede any deep chunk.
        first_two = {job.base for job in jobs[:2]}
        self.assertEqual(len(first_two), 2)
        starts = [job.moves[0] for job in jobs]
        self.assertEqual(starts, sorted(starts))


if __name__ == "__main__":
    unittest.main()
