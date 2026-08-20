import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sylver.g4_candidate_certificates import (
    G4_MOVE_90_NATIVE_FINITE_P_POSITIONS,
    G4_MOVE_90_WIDE_NATIVE_FINITE_P_POSITIONS,
)
from sylver.short_certificates import SHORT_NATIVE_FINITE_P_POSITIONS
from sylver.solver import solve_position


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sylver" / "native_solver.cpp"


class NativeSylverSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        compiler = shutil.which("g++")
        if compiler is None:
            raise unittest.SkipTest("g++ is required for the native solver controls")
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.temporary_directory.name) / "native_solver"
        subprocess.run(
            [
                compiler,
                "-std=c++20",
                "-O3",
                "-Wall",
                "-Wextra",
                "-pedantic",
                str(SOURCE),
                "-o",
                str(cls.binary),
            ],
            check=True,
            cwd=ROOT,
        )
        cls.wide_binary = Path(cls.temporary_directory.name) / "native_solver_1023"
        subprocess.run(
            [
                compiler,
                "-std=c++20",
                "-O3",
                "-Wall",
                "-Wextra",
                "-pedantic",
                "-DSYLVER_NATIVE_WORDS=16",
                str(SOURCE),
                "-o",
                str(cls.wide_binary),
            ],
            check=True,
            cwd=ROOT,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    def native_result(
        self, generators: tuple[int, ...], *, wide: bool = False
    ) -> tuple[bool, int | None, int]:
        completed = subprocess.run(
            [
                str(self.wide_binary if wide else self.binary),
                *(str(value) for value in generators),
            ],
            check=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        fields = dict(field.split("=", 1) for field in completed.stdout.split()[1:])
        return (
            completed.stdout.startswith("N "),
            None if fields["winning_move"] == "none" else int(fields["winning_move"]),
            int(fields["frobenius"]),
        )

    def test_native_solver_matches_reference_controls(self) -> None:
        controls = (
            (2, 3),
            (4, 5),
            (5, 7),
            (7, 8, 13),
            (16, 20, 28, 35, 54),
        )
        for generators in controls:
            with self.subTest(generators=generators):
                reference = solve_position(generators)
                self.assertEqual(
                    self.native_result(generators),
                    (reference.is_winning, reference.winning_move, reference.frobenius),
                )

    def test_native_solver_reproduces_hard_branches(self) -> None:
        # Deep children of the short nodes T={16,20,34} and V={16,26,36,56}
        # are too slow for the Python evaluator inside every suite run; the
        # Python reference reproduced T's entry (3,407,297 states) and every
        # V entry it attempted, including {16,26,36,56,102,201} with exactly
        # the native state count 27,865,056.
        short_native = {
            (16, 20, 34, 58, 291): 353,
            (16, 26, 30, 36, 99): 169,
            (16, 26, 36, 44, 56, 57): 123,
            (16, 26, 36, 46, 56, 153): 239,
            (16, 26, 36, 50, 56, 109): 179,
            (16, 26, 36, 54, 56, 83): 159,
            (16, 26, 36, 53, 56, 66): 139,
            (16, 26, 36, 37, 56, 70): 113,
            (16, 26, 36, 56, 76, 131): 217,
            (16, 26, 36, 55, 56, 86): 131,
            (16, 26, 36, 56, 102, 201): 287,
        }
        self.assertEqual(
            SHORT_NATIVE_FINITE_P_POSITIONS, set(short_native)
        )
        for generators, frobenius in short_native.items():
            with self.subTest(generators=generators):
                self.assertEqual(
                    self.native_result(generators),
                    (False, None, frobenius),
                )
        self.assertEqual(
            self.native_result((16, 20, 28, 66, 81)),
            (True, 107, 171),
        )
        self.assertEqual(
            self.native_result((16, 20, 28, 66, 305)),
            (False, None, 395),
        )
        self.assertEqual(
            self.native_result((16, 20, 28, 70, 277)),
            (False, None, 371),
        )
        self.assertEqual(
            self.native_result((16, 20, 28, 74, 273)),
            (False, None, 371),
        )
        self.assertEqual(
            self.native_result((16, 20, 28, 82, 145)),
            (False, None, 251),
        )
        self.assertEqual(
            self.native_result((16, 20, 28, 86, 105)),
            (False, None, 215),
        )
        move_90_frobenius = {
            (16, 20, 28, 45, 98): 147,
            (16, 20, 28, 47, 82, 90): 133,
            (16, 20, 28, 51, 66, 90): 129,
            (16, 20, 28, 55, 90, 94): 157,
            (16, 20, 28, 86, 90, 227): 325,
            (16, 20, 28, 90, 114, 331): 433,
        }
        self.assertEqual(
            set(move_90_frobenius), G4_MOVE_90_NATIVE_FINITE_P_POSITIONS
        )
        for generators, frobenius in move_90_frobenius.items():
            with self.subTest(generators=generators):
                self.assertEqual(
                    self.native_result(generators),
                    (False, None, frobenius),
                )

    def test_native_solver_rejects_non_coprime_input(self) -> None:
        completed = subprocess.run(
            [str(self.binary), "16", "20", "28", "66"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("gcd one", completed.stderr)

    def test_wide_native_solver_reproduces_move_90_reply_12(self) -> None:
        generators = (12, 16, 20, 90, 825)
        self.assertEqual(
            G4_MOVE_90_WIDE_NATIVE_FINITE_P_POSITIONS,
            {generators},
        )
        self.assertEqual(
            self.native_result(generators, wide=True),
            (False, None, 923),
        )

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


if __name__ == "__main__":
    unittest.main()
