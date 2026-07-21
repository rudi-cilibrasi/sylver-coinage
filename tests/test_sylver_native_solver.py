import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    def native_result(self, generators: tuple[int, ...]) -> tuple[bool, int | None, int]:
        completed = subprocess.run(
            [str(self.binary), *(str(value) for value in generators)],
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

    def test_native_solver_rejects_non_coprime_input(self) -> None:
        completed = subprocess.run(
            [str(self.binary), "16", "20", "28", "66"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("gcd one", completed.stderr)


if __name__ == "__main__":
    unittest.main()
