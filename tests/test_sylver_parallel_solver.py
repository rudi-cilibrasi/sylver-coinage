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
        # A deliberately broken build that never tries move 7 (a missed
        # child): --verify-memo must reject what it memoizes.
        cls.faulty = Path(cls.tmp.name) / 'parallel_solver-faulty'
        subprocess.run([compiler, '-std=c++20', '-O2', '-pthread', '-DSYLVER_NATIVE_WORDS=2',
                        '-DSYLVER_PARALLEL_TEST_SKIP_MOVE=7', str(ROOT / 'sylver' / 'parallel_solver.cpp'),
                        '-o', str(cls.faulty)], check=True)

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
            native = self.run_solver('native_solver', 2, *gens).split()
            if native[0] == 'N':
                # Random positions are mostly N; each N position plus its
                # winning move is a P position, where a missed child would
                # show up as a false N.
                child = sorted({*gens, int(native[1].split('=')[1])})
                self.assert_decides_like_native(2, child, '--threads', threads, '--split-depth', depth)

    def test_verify_memo_accepts_honest_searches(self):
        for index, gens in enumerate(random_positions(31, 40, 110)):
            threads = (1, 2, 4, 8)[index % 4]
            for args in (['--threads', threads, '--verify-memo', *gens],
                         ['--threads', threads, '--verify-memo', '--odd-range', 3, 21, 16, 26]):
                result = subprocess.run([str(self.binaries['parallel_solver', 4]), *map(str, args)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (args, result.stderr))
                states = result.stdout.split()[-1].split('=')[1]
                self.assertEqual(result.stderr, f'parallel_solver: memo verified ({states} entries)\n', args)
                if index % 4:
                    break   # the sweep once per thread count is enough

    def test_verify_memo_rejects_a_search_that_misses_a_child(self):
        # {9,11,13} is P; the faulty build calls it N. {5,8} is N either way,
        # but the faulty memo still holds false P entries.
        for gens, outcome in (((9, 11, 13), 'P'), ((5, 8), 'N'), ((12, 15, 19), 'N')):
            self.assertEqual(self.run_solver('native_solver', 2, *gens).split()[0], outcome)
            for threads in (1, 3):
                result = subprocess.run([str(self.faulty), '--threads', str(threads), '--verify-memo', *map(str, gens)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, gens)
                self.assertIn('memo verification failed', result.stderr, gens)

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
            # State counts vary with the threads' order (and can fall below
            # the sequential count), so only the outcome is fixed.
            out = self.run_solver('parallel_solver', 4, '--threads', 6, '--verify-memo', 16, 26, 33, 62, 89, 102).split()
            self.assertEqual(out[:3], ['P', 'winning_move=none', 'frobenius=119'])

    def test_sweep_with_one_thread_prints_exactly_what_native_prints(self):
        for args in (['--odd-range', 3, 41, 16, 26], ['--odd-list', '45,9,31', 12, 20, 22],
                     ['--odd-range', 3, 29, 10, 14]):
            self.assertEqual(self.run_solver('parallel_solver', 4, '--threads', 1, *args),
                             self.run_solver('native_solver', 4, *args), args)

    def test_sweep_with_threads_decides_every_row_like_native(self):
        native = self.run_solver('native_solver', 4, '--odd-range', 3, 41, 16, 26).splitlines()
        for threads in (3, 8):
            rows = self.run_solver('parallel_solver', 4, '--threads', threads, '--odd-range', 3, 41, 16, 26).splitlines()
            self.assertEqual([r.split()[:2] + r.split()[3:4] for r in rows],
                             [r.split()[:2] + r.split()[3:4] for r in native])
            for row in rows:
                move, outcome, winning = row.split()[:3]
                if outcome == 'N':   # a winning move of 16,26,move: its child must be P
                    child = self.run_solver('native_solver', 4, 16, 26, move.split('=')[1], winning.split('=')[1])
                    self.assertEqual(child.split()[0], 'P', row)

    def test_stop_at_p_ends_the_sweep_after_the_first_p_row(self):
        # {4,6,9}+5 and +7 are N, {4,6,9,11} is P, {4,6,9,13} is N.
        native = self.run_solver('native_solver', 2, '--odd-list', '5,7,11,13', 4, 6, 9).splitlines()
        self.assertEqual([row.split()[1] for row in native], ['N', 'N', 'P', 'N'])
        for threads in (1, 2):
            rows = self.run_solver('parallel_solver', 2, '--threads', threads, '--stop-at-p',
                                   '--odd-list', '5,7,11,13', 4, 6, 9).splitlines()
            self.assertEqual([row.split()[:2] for row in rows], [['move=5', 'N'], ['move=7', 'N'], ['move=11', 'P']])

    def test_rejects_bad_arguments(self):
        binary = str(self.binaries['parallel_solver', 2])
        for args in (['--threads', '0', '4', '5'], ['--threads', 'x', '4', '5'], ['--split-depth', '-1', '4', '5'],
                     ['--bogus', '1', '4', '5'], ['4', '6'], ['--threads', '2'], ['16', '26', '62', '95', '98', '102'],
                     ['--odd-range', '4', '9', '16', '26'], ['--odd-list', '9,10', '16', '26'], ['--odd-range', '5', '3', '16', '26'], ['4', '7', '--split-depth', '3'],
                     ['--threads', '2', '--split-depth', '0', '4', '5'], ['50000', '50001'], ['4', '5x'],
                     ['--odd-list', '3', '6', '9'], ['--threads']):
            result = subprocess.run([binary, *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, args)
            self.assertEqual(result.stdout, '', args)
            self.assertTrue(result.stderr.startswith('parallel_solver: '), (args, result.stderr))


if __name__ == '__main__':
    unittest.main()
