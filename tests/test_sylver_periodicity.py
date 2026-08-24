import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sylver.periodicity import PeriodicityEngine, TailReport, analyze_odd_tail
from sylver.solver import solve_position


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sylver" / "periodicity_engine.cpp"


class PeriodicityReferenceTests(unittest.TestCase):
    def test_translated_recurrence_matches_exact_solver(self) -> None:
        # Each range crosses auto_min = 2*F(base/2)+2, so these are tests of
        # the translated finite-state recurrence rather than only its exact
        # base-region fallback.  The middle case has the genuine P-child 7.
        cases = (
            ((2,), 31),
            ((4, 6), 31),
            ((6, 16), 79),
            ((8, 10, 22), 79),
        )
        for base, endpoint in cases:
            with self.subTest(base=base):
                engine = PeriodicityEngine(base)
                for move in range(3, endpoint + 1, 2):
                    expected = solve_position((*base, move)).winning_move is None
                    self.assertEqual(engine.outcome_single(move), expected)

    def test_small_tail_certificates(self) -> None:
        expected = (
            TailReport((2,), 0, (3,), 9, 5, 4),
            TailReport((4, 6), 2, (), 13, 9, 4),
            TailReport((6, 16), 26, (7,), 61, 57, 4),
            # Published long P-position: every odd child is N.
            TailReport((8, 10, 22), 14, (), 57, 49, 8),
        )
        self.assertEqual(
            tuple(analyze_odd_tail(report.generators, 201) for report in expected),
            expected,
        )

    def test_requires_gcd_two(self) -> None:
        with self.assertRaisesRegex(ValueError, "gcd-two"):
            PeriodicityEngine((5, 7))


class NativePeriodicityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        compiler = shutil.which("g++")
        if compiler is None:
            raise unittest.SkipTest("g++ is required for the native engine test")
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tempdir.name) / "periodicity_engine"
        subprocess.run(
            [
                compiler,
                "-std=c++20",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                str(SOURCE),
                "-o",
                str(cls.binary),
            ],
            check=True,
            cwd=ROOT,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def run_engine(
        self,
        limit: int,
        base: tuple[int, ...],
        options: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        cache = Path(self.tempdir.name) / ("-".join(map(str, base)) + ".cache")
        completed = subprocess.run(
            [
                str(self.binary),
                str(cache),
                str(limit),
                *options,
                *map(str, base),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        return tuple(completed.stdout.splitlines())

    def test_native_engine_matches_reference_certificates(self) -> None:
        cases = (
            ((2,), "PERIOD start=5 length=4 shapes=1", ("P-HIT n=3",)),
            ((4, 6), "PERIOD start=9 length=4 shapes=3", ()),
            ((6, 16), "PERIOD start=57 length=4 shapes=2", ("P-HIT n=7",)),
            ((8, 10, 22), "PERIOD start=49 length=8 shapes=50", ()),
        )
        for base, period, hits in cases:
            with self.subTest(base=base):
                output = self.run_engine(201, base)
                self.assertIn(period, output)
                self.assertEqual(
                    tuple(line for line in output if line.startswith("P-HIT")),
                    hits,
                )

    def test_native_engine_reuses_exact_x_campaign_rows(self) -> None:
        records = (
            str(ROOT / "sylver" / "move26_data" / "full_82.txt"),
            str(ROOT / "sylver" / "move26_data" / "x_sortie.txt"),
        )
        options = tuple(value for path in records for value in ("--base-record", path))
        output = self.run_engine(407, (16, 26, 82, 88), options)
        self.assertIn("LIMIT-REACHED n=407 shapes=1", output)
        self.assertEqual(
            tuple(line for line in output if line.startswith("P-HIT")),
            (),
        )

    def test_native_active_row_checkpoint_resumes_safely(self) -> None:
        cache = Path(self.tempdir.name) / "checkpoint-resume.cache"
        checkpoint = Path(f"{cache}.rowstate")
        first = subprocess.run(
            [
                str(self.binary),
                str(cache),
                "201",
                "--stop-after-evaluations",
                "25",
                "8",
                "10",
                "22",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        self.assertEqual(first.returncode, 75, first.stderr)
        self.assertTrue(checkpoint.is_file())
        self.assertIn("ROW-CHECKPOINT saved", first.stdout)

        # The state is proof input, so accidental corruption must fail closed.
        corrupt_checkpoint = Path(self.tempdir.name) / "corrupt.rowstate"
        corrupt_data = bytearray(checkpoint.read_bytes())
        corrupt_data[-1] ^= 1
        corrupt_checkpoint.write_bytes(corrupt_data)
        corrupt = subprocess.run(
            [
                str(self.binary),
                str(cache),
                "201",
                "--checkpoint-file",
                str(corrupt_checkpoint),
                "8",
                "10",
                "22",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        self.assertEqual(corrupt.returncode, 2)
        self.assertIn("checksum mismatch", corrupt.stderr)

        resumed = subprocess.run(
            [str(self.binary), str(cache), "201", "8", "10", "22"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        output = tuple(resumed.stdout.splitlines())
        self.assertTrue(any(line.startswith("ROW-CHECKPOINT loaded") for line in output))
        self.assertTrue(
            any(line.startswith("PERIOD ") and "length=8 shapes=50" in line
                for line in output)
        )
        self.assertFalse(checkpoint.exists())
        self.assertEqual(
            tuple(line for line in output if line.startswith("P-HIT")),
            (),
        )

    def test_loaded_absolute_cache_is_flushed_before_period_search(self) -> None:
        # {4,6} is P, so its legal child after 101 is exactly N.  Merely
        # loading that absolute shortcut must defer cycle detection until the
        # anchor and a complete tbar window have passed.
        cache = Path(self.tempdir.name) / "absolute-cache.txt"
        cache.write_text("4,6,101 0\n")
        completed = subprocess.run(
            [str(self.binary), str(cache), "101", "4", "6"],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        output = tuple(completed.stdout.splitlines())
        self.assertIn("LIMIT-REACHED n=101 shapes=3", output)
        self.assertFalse(any(line.startswith("PERIOD") for line in output))

    def test_exact_threads_reproduce_all_period_certificates(self) -> None:
        # Distinct cache paths: a shared cache would raise the loaded-anchor
        # bound and legitimately defer period search for the legacy tests.
        cases = (
            ((2,), "PERIOD start=5 length=4 shapes=1", ("P-HIT n=3",)),
            ((4, 6), "PERIOD start=9 length=4 shapes=3", ()),
            ((6, 16), "PERIOD start=57 length=4 shapes=2", ("P-HIT n=7",)),
            ((8, 10, 22), "PERIOD start=49 length=8 shapes=50", ()),
        )
        for base, period, hits in cases:
            with self.subTest(base=base):
                cache = Path(self.tempdir.name) / (
                    "mt-" + "-".join(map(str, base)) + ".cache"
                )
                completed = subprocess.run(
                    [
                        str(self.binary),
                        str(cache),
                        "201",
                        "--exact-threads",
                        "4",
                        *map(str, base),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=ROOT,
                    timeout=60,
                )
                output = tuple(completed.stdout.splitlines())
                self.assertIn(period, output)
                self.assertEqual(
                    tuple(line for line in output if line.startswith("P-HIT")),
                    hits,
                )

    def test_exact_threads_serial_and_parallel_caches_agree(self) -> None:
        # Collect mode keeps scanning siblings past an unknown child, so it
        # can solve dependencies that the serial early-exit never needed.
        # The caches may therefore differ as sets; they must never conflict
        # on a shared key, and the period certificate must be identical.
        outcomes = {}
        periods = {}
        for label, threads in (("serial", "1"), ("parallel", "4")):
            cache = Path(self.tempdir.name) / f"threads-{label}.cache"
            completed = subprocess.run(
                [
                    str(self.binary),
                    str(cache),
                    "201",
                    "--exact-threads",
                    threads,
                    "8",
                    "10",
                    "22",
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=60,
            )
            rows = {}
            for line in cache.read_text().splitlines():
                key, _, value = line.rpartition(" ")
                rows[key] = value
            outcomes[label] = rows
            periods[label] = tuple(
                line
                for line in completed.stdout.splitlines()
                if line.startswith("PERIOD")
            )
        shared = set(outcomes["serial"]) & set(outcomes["parallel"])
        self.assertGreater(len(shared), 0)
        for key in shared:
            self.assertEqual(
                outcomes["serial"][key],
                outcomes["parallel"][key],
                f"conflicting outcome for {key}",
            )
        self.assertEqual(periods["serial"], periods["parallel"])
        self.assertEqual(
            periods["serial"], ("PERIOD start=49 length=8 shapes=50",)
        )

    def test_memory_report_accounts_for_subsystems(self) -> None:
        cache = Path(self.tempdir.name) / "memreport.cache"
        completed = subprocess.run(
            [
                str(self.binary),
                str(cache),
                "201",
                "--memory-report",
                "8",
                "10",
                "22",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=60,
        )
        lines = [
            line
            for line in completed.stdout.splitlines()
            if line.startswith("MEMORY ")
        ]
        self.assertTrue(lines, "no MEMORY report emitted")
        fields = dict(
            part.split("=", 1) for part in lines[-1].split()[1:] if "=" in part
        )
        self.assertIn("total", fields)
        total = int(fields.pop("total"))
        self.assertGreater(total, 0)
        self.assertIn("shapes", fields)
        self.assertIn("transitions", fields)
        self.assertIn("index", fields)
        self.assertIn("ring", fields)
        parts_sum = sum(int(value) for value in fields.values())
        self.assertAlmostEqual(parts_sum / total, 1.0, delta=0.01)

    def test_exact_threads_rejects_invalid_counts(self) -> None:
        for bad in ("0", "-2", "65", "x"):
            cache = Path(self.tempdir.name) / "bad-threads.cache"
            completed = subprocess.run(
                [str(self.binary), str(cache), "31", "--exact-threads", bad, "4", "6"],
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=30,
            )
            self.assertNotEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
