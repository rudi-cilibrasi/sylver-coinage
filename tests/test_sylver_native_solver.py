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
        # The deep child of short node T={16,20,34} after the even move 58:
        # the Python reference reproduced the same P outcome once with
        # 3,407,297 states, which is too slow for every suite run.
        self.assertEqual(
            SHORT_NATIVE_FINITE_P_POSITIONS, {(16, 20, 34, 58, 291)}
        )
        self.assertEqual(
            self.native_result((16, 20, 34, 58, 291)),
            (False, None, 353),
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


if __name__ == "__main__":
    unittest.main()
