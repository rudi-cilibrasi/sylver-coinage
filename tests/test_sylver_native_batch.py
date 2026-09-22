"""Mixed-position batches must retain exact finite-game semantics."""

import itertools
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import frobenius_number, solve_position

SOURCE = Path(__file__).resolve().parents[1] / "sylver/native_solver.cpp"
ROW = re.compile(r"position=([\d,]+) ([PN]) winning_move=(none|\d+) "
                 r"frobenius=(\d+) cumulative_states=(\d+)")


@unittest.skipUnless(shutil.which("g++"), "requires g++")
class NativeBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.directory.name) / "native"
        subprocess.run(["g++", "-std=c++20", "-O2", "-Wall", "-Wextra",
                        "-pedantic", "-DSYLVER_NATIVE_WORDS=2", str(SOURCE),
                        "-o", str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def batch(self, text, hints=()):
        path = Path(self.directory.name) / "positions.txt"
        path.write_text(text)
        command = [str(self.binary)]
        if hints:
            command += ["--hints", ",".join(map(str, hints))]
        return subprocess.run([*command, "--batch-file", str(path)],
                              capture_output=True, text=True, timeout=20)

    def test_mixed_bounds_outcomes_and_witnesses_match_python(self):
        positions = sorted({
            minimal_generators(gs)
            for count in (2, 3, 4)
            for gs in itertools.combinations(range(2, 13), count)
            if math.gcd(*gs) == 1 and frobenius_number(gs) <= 45
        }, reverse=True)
        positions += [(2, 67), (2, 3), (4, 5, 7)]
        result = self.batch("\n".join(",".join(map(str, gs)) for gs in positions))
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = result.stdout.splitlines()
        self.assertEqual(len(rows), len(positions))
        previous_count = 0
        for gs, line in zip(positions, rows):
            with self.subTest(position=gs):
                row = ROW.fullmatch(line)
                self.assertIsNotNone(row)
                self.assertEqual(tuple(map(int, row[1].split(','))), gs)
                self.assertEqual(int(row[4]), frobenius_number(gs))
                self.assertGreaterEqual(int(row[5]), previous_count)
                previous_count = int(row[5])
                expected = solve_position(gs)
                self.assertEqual(row[2] == "N", expected.is_winning)
                if row[3] != "none":
                    winner = int(row[3])
                    self.assertFalse(is_generated(gs, winner))
                    self.assertFalse(solve_position((*gs, winner)).is_winning)

    def test_duplicate_position_reuses_exact_memo_with_hints(self):
        result = self.batch("8,13\n2,3\n13,8,8\n", hints=(7, 9))
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [ROW.fullmatch(line) for line in result.stdout.splitlines()]
        self.assertEqual(rows[0].group(2, 3), rows[2].group(2, 3))
        self.assertEqual(rows[1][5], rows[2][5])

    def test_all_rows_are_validated_before_any_outcome_is_printed(self):
        for text in ("", "2,3\n4,6\n", "2,3\n1,3\n", "2,3\n3,5junk\n",
                     "2,3\n29,31\n", "2,3\n3,,5\n"):
            with self.subTest(text=text):
                result = self.batch(text)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
