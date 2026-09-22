"""Targeted translated evaluation must agree with finite game evaluation."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sylver.solver import solve_position
from sylver.targeted import TargetedEngine

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sylver/periodicity_engine.cpp"
TARGET = re.compile(r"^TARGET n=(\d+) outcome=([PN]) shapes=(\d+) .*", re.M)
BASES = ((2,), (4, 6), (6, 16), (8, 10, 22), (8, 14),
         (6, 8, 10), (6, 10, 14), (8, 10, 14))


class TargetedReferenceTests(unittest.TestCase):
    def test_nonmonotone_queries_match_independent_finite_solver(self):
        for base in BASES:
            engine = TargetedEngine(base)
            # Start far beyond the base region, then go backwards across
            # actual translated P hits and reset cutoffs, then forwards.
            for n in (65, 3, 17, 25, 7, 31, 19, 23, 49, 67):
                with self.subTest(base=base, target=n):
                    self.assertEqual(engine.outcome_single(n),
                                     not solve_position((*base, n)).is_winning)
            self.assertEqual(engine.scanned_to, 1)

    def test_sparse_state_cannot_be_used_as_a_period_certificate(self):
        engine = TargetedEngine((8, 10, 22))
        engine.outcome_single(65)
        with self.assertRaises(RuntimeError):
            engine.snapshot()
        with self.assertRaises(RuntimeError):
            engine.step()

    def test_invalid_targets(self):
        engine = TargetedEngine((4, 6))
        for n in (1, 2, -1, 3.0, True):
            with self.assertRaises(ValueError):
                engine.outcome_single(n)


@unittest.skipUnless(shutil.which("g++"), "requires g++")
class NativeTargetedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.directory.name) / "engine"
        subprocess.run(["g++", "-std=c++20", "-O2", "-Wall", "-Wextra",
                        "-pedantic", "-pthread", str(SOURCE), "-o", str(cls.binary)],
                       check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def run_target(self, base, n, cache, options=()):
        return subprocess.run([str(self.binary), str(cache), str(n),
                               "--target-only", *options, *map(str, base)],
                              capture_output=True, text=True, timeout=30)

    def test_cold_queries_and_parallel_unknowns_match_finite_solver(self):
        for base in BASES:
            for n in (17, 25, 65):
                for threads in (1, 3):
                    with self.subTest(base=base, n=n, threads=threads):
                        with tempfile.TemporaryDirectory() as directory:
                            cache = Path(directory) / "outcomes.cache"
                            result = self.run_target(base, n, cache,
                                ("--exact-threads", str(threads), "--batch-pending", "2"))
                            self.assertEqual(result.returncode, 0, result.stderr)
                            match = TARGET.search(result.stdout)
                            self.assertIsNotNone(match, result.stdout)
                            self.assertEqual(match[2] == "N",
                                             solve_position((*base, n)).is_winning)
                            self.assertNotIn("PERIOD", result.stdout)
                            self.assertFalse(Path(str(cache) + ".rowstate").exists())

    def test_interruption_preserves_only_exact_cache_and_existing_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "outcomes.cache"
            checkpoint = Path(str(cache) + ".rowstate")
            checkpoint.write_bytes(b"unrelated periodicity checkpoint")
            interrupted = self.run_target((8, 10, 22), 65, cache,
                                          ("--stop-after-evaluations", "25"))
            self.assertEqual(interrupted.returncode, 75, interrupted.stderr)
            self.assertIn("outcome=unknown", interrupted.stdout)
            self.assertEqual(checkpoint.read_bytes(), b"unrelated periodicity checkpoint")
            resumed = self.run_target((8, 10, 22), 65, cache)
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertEqual(TARGET.search(resumed.stdout)[2], "N")
            self.assertEqual(checkpoint.read_bytes(), b"unrelated periodicity checkpoint")
            # A completed targeted result is reusable as an exact finite
            # outcome, regardless of any unfinished automaton checkpoint.
            repeated = self.run_target((8, 10, 22), 65, cache)
            self.assertIn("exact_completed=0", repeated.stdout)
            self.assertIn("evaluations=1", repeated.stdout)

    def test_incompatible_checkpoint_argument_and_invalid_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "outcomes.cache"
            result = self.run_target((4, 6), 17, cache,
                                     ("--checkpoint-file", str(cache) + ".custom"))
            self.assertNotEqual(result.returncode, 0)
            for n in (1, 2, 0, -3, 2**32 + 1, "17suffix", "17.0"):
                result = self.run_target((4, 6), n, cache)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("TARGET", result.stdout)

    def test_cached_reset_witness_avoids_unnecessary_unknown_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "outcomes.cache"
            self.assertFalse(solve_position((6, 10, 14, 17)).is_winning)
            cache.write_text("6,10,14,17 1\n")
            result = self.run_target((6, 10, 14), 65, cache)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(TARGET.search(result.stdout)[2], "N")
            self.assertIn("evaluations=2", result.stdout)
            self.assertIn("exact_completed=0", result.stdout)
            # A P for a different even part cannot serve as this reset.
            cache.write_text("6,10,14,17 1\n")
            result = self.run_target((8, 10, 22), 65, cache)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(TARGET.search(result.stdout)[2], "N")
            self.assertNotIn("exact_completed=0", result.stdout)

    def test_target_ranges_reuse_sparse_state_and_stop_on_actual_p(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "outcomes.cache"
            result = self.run_target((6, 10, 14), 65, cache,
                                     ("--target-start", "3", "--stop-on-p"))
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = TARGET.findall(result.stdout)
            self.assertEqual([int(row[0]) for row in rows], list(range(3, 18, 2)))
            self.assertEqual(rows[-1][1], "P")
            for n, outcome, _ in rows:
                self.assertEqual(outcome == "N", solve_position((6, 10, 14, int(n))).is_winning)
            cache.unlink()
            result = self.run_target((8, 10, 22), 65, cache,
                                     ("--target-start", "49", "--exact-threads", "3"))
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = TARGET.findall(result.stdout)
            self.assertEqual([int(row[0]) for row in rows], list(range(49, 66, 2)))
            self.assertTrue(all(row[1] == "N" for row in rows))
            self.assertNotIn("PERIOD", result.stdout)

    def test_invalid_range_options_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "outcomes.cache"
            for start in (0, 2, 18, "3bad", 2**32 + 1):
                result = self.run_target((4, 6), 17, cache,
                                         ("--target-start", str(start)))
                self.assertNotEqual(result.returncode, 0)
            result = subprocess.run([str(self.binary), str(cache), "17",
                                     "--stop-on-p", "4", "6"],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
