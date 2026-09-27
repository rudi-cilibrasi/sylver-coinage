import random
import shutil
import subprocess
import tempfile
import unittest
from functools import reduce
from math import gcd
from pathlib import Path

from sylver.solver import frobenius_number

ROOT = Path(__file__).resolve().parents[1]


def random_positions(seed, count, max_frobenius, pool=45):
    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        gens = sorted(rng.sample(range(3, pool), rng.randint(2, 5)))
        if reduce(gcd, gens) == 1 and frobenius_number(gens) <= max_frobenius:
            positions.append(gens)
    return positions


class ParallelSolverTests(unittest.TestCase):
    """parallel_solver.cpp must decide every position exactly as native_solver.cpp does."""

    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if compiler is None:
            raise unittest.SkipTest('g++ is required')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binaries = {}
        for name in ('native_solver', 'parallel_solver'):
            for words in (2, 4):
                binary = Path(cls.tmp.name) / f'{name}-{words}'
                subprocess.run([compiler, '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror',
                                '-pthread', f'-DSYLVER_NATIVE_WORDS={words}',
                                str(ROOT / 'sylver' / f'{name}.cpp'), '-o', str(binary)], check=True)
                cls.binaries[name, words] = binary

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_solver(self, name, words, *args):
        return subprocess.run([str(self.binaries[name, words]), *map(str, args)],
                              capture_output=True, text=True, check=True).stdout

    def assert_decides_like_native(self, words, gens, *options):
        native = self.run_solver('native_solver', words, *gens).split()
        parallel = self.run_solver('parallel_solver', words, *options, *gens).split()
        self.assertEqual(parallel[0], native[0], (gens, options))   # outcome
        self.assertEqual(parallel[2], native[2], (gens, options))   # Frobenius number
        if parallel[0] == 'N':
            # Any winning move is a valid answer: its child must be P.
            move = int(parallel[1].split('=')[1])
            self.assertNotIn(move, gens)
            child = self.run_solver('native_solver', words, *gens, move).split()
            self.assertEqual(child[0], 'P', (gens, move, options))
        else:
            self.assertEqual(parallel[1], 'winning_move=none')

    def test_one_thread_prints_exactly_what_native_prints(self):
        for gens in random_positions(20260927, 120, 100):
            self.assertEqual(self.run_solver('parallel_solver', 2, '--threads', 1, *gens),
                             self.run_solver('native_solver', 2, *gens), gens)

    def test_many_threads_decide_every_position_like_native(self):
        positions = random_positions(9, 60, 110)
        for index, gens in enumerate(positions):
            threads = (2, 3, 8)[index % 3]
            depth = (1, 3, 6, 40)[index % 4]
            self.assert_decides_like_native(2, gens, '--threads', threads, '--split-depth', depth)

    def test_repeated_runs_on_larger_positions(self):
        # Larger searches give threads time to interleave; every repetition
        # must reach the native outcome.
        positions = random_positions(5, 6, 180, pool=60)
        for gens in positions:
            for threads in (4, 8, 16):
                self.assert_decides_like_native(4, gens, '--threads', threads)

    def test_campaign_control(self):
        # {16,26,33,62,89,102} is P with exactly 1,721,485 states (PR #13).
        self.assertEqual(self.run_solver('parallel_solver', 4, '--threads', 1, 16, 26, 33, 62, 89, 102).strip(),
                         'P winning_move=none frobenius=119 states=1721485')
        for _ in range(3):
            out = self.run_solver('parallel_solver', 4, '--threads', 6, 16, 26, 33, 62, 89, 102).split()
            self.assertEqual(out[:3], ['P', 'winning_move=none', 'frobenius=119'])
            # Threads may briefly evaluate the same state; it is stored once.
            self.assertGreaterEqual(int(out[3].split('=')[1]), 1721485)

    def test_rejects_bad_arguments(self):
        binary = str(self.binaries['parallel_solver', 2])
        for args in (['--threads', '0', '4', '5'], ['--threads', 'x', '4', '5'], ['--split-depth', '-1', '4', '5'],
                     ['--bogus', '1', '4', '5'], ['4', '6'], ['--threads', '2'], ['16', '26', '62', '95', '98', '102']):
            result = subprocess.run([binary, *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, args)
            self.assertEqual(result.stdout, '', args)
            self.assertTrue(result.stderr.startswith('parallel_solver: '), (args, result.stderr))


if __name__ == '__main__':
    unittest.main()
