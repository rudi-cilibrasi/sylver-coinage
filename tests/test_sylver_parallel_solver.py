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

        def build(name, words, *flags, label=None):
            binary = Path(cls.tmp.name) / f'{label or name}-{words}'
            subprocess.run([compiler, '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror', '-pthread',
                            f'-DSYLVER_NATIVE_WORDS={words}', *flags, str(ROOT / 'sylver' / f'{name}.cpp'),
                            '-o', str(binary)], check=True)
            return binary
        for name in ('native_solver', 'parallel_solver'):
            for words in (1, 2, 4, 6):
                cls.binaries[name, words] = build(name, words)
        # The BMI2 pext/pdep path that discovery builds use.
        cls.native_arch = build('parallel_solver', 4, '-march=native', label='parallel_solver-native-arch')
        # Deliberately broken builds that --verify-memo must reject: one never
        # tries move 7 (a missed child); one forges a root "winning" by naming 1.
        cls.faulty = build('parallel_solver', 2, '-DSYLVER_PARALLEL_TEST_SKIP_MOVE=7', label='faulty')
        cls.forged = build('parallel_solver', 2, '-DSYLVER_PARALLEL_TEST_FORGE_MOVE_ONE', label='forged')
        # The cross-check build with Kunz-coordinate memo keys.
        cls.kunz_keys = build('parallel_solver', 4, '-DSYLVER_PARALLEL_KUNZ_KEYS', label='kunz-keys')

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
        # Other word counts, including keys packed across 64-bit boundaries.
        for words, gens in ((1, (4, 7)), (1, (5, 9, 11)), (6, (16, 26, 33, 62, 89)), (6, (11, 13, 17, 19))):
            self.assertEqual(self.run_solver('parallel_solver', words, '--threads', 1, *gens),
                             self.run_solver('native_solver', words, *gens), (words, gens))

    def test_bmi2_build_decides_like_native(self):
        for index, gens in enumerate(random_positions(77, 30, 120)):
            native = self.run_solver('native_solver', 4, *gens)
            exact = subprocess.run([str(self.native_arch), '--threads', '1', *map(str, gens)],
                                   capture_output=True, text=True, check=True).stdout
            self.assertEqual(exact, native, gens)
            threaded = subprocess.run([str(self.native_arch), '--threads', str(2 + index % 4), '--verify-memo',
                                       *map(str, gens)], capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(threaded[0], native.split()[0], gens)
            self.assertTrue(threaded[-1].startswith('entries='), gens)

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
            depth = (1, 3, 6, 40, 60)[index % 5]
            for args in (['--threads', threads, '--split-depth', depth, '--verify-memo', *gens],
                         ['--threads', threads, '--split-depth', depth, '--verify-memo', '--odd-range', 3, 21, 16, 26]):
                result = subprocess.run([str(self.binaries['parallel_solver', 4]), *map(str, args)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (args, result.stderr))
                *rows, last = result.stdout.splitlines()
                states = rows[-1].split()[-1].split('=')[1]
                self.assertEqual(last, f'verified entries={states}', args)
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
                self.assertNotIn('verified', result.stdout, gens)

    def test_verify_memo_rejects_a_root_that_names_1(self):
        # Naming 1 reaches the semigroup of every integer, which has no moves;
        # an entry claiming that as a win must fail however it is presented.
        for gens in ((9, 11, 13), (5, 8)):
            for args in (['--threads', '2', '--verify-memo', *map(str, gens)],
                         ['--threads', '1', '--verify-memo', '--odd-list', '3', '4', '6']):
                result = subprocess.run([str(self.forged), *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, args)
                self.assertIn('memo verification failed', result.stderr, args)
                self.assertNotIn('verified', result.stdout, args)

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
        for threads in (3, 8):
            rows = self.run_solver('parallel_solver', 4, '--threads', threads, '--odd-range', 3, 41, 16, 26).splitlines()
            self.assertEqual(len(rows), 20)
            for row in rows:
                move, outcome, winning, frobenius = row.split()[:4]
                move = move.split('=')[1]
                # Each row against a separate single-position native run.
                single = self.run_solver('native_solver', 4, 16, 26, move).split()
                self.assertEqual([outcome, frobenius], [single[0], single[2]], row)
                if outcome == 'N':   # a winning move of 16,26,move: its child must be P
                    child = self.run_solver('native_solver', 4, 16, 26, move, winning.split('=')[1])
                    self.assertEqual(child.split()[0], 'P', row)

    def test_stop_at_p_ends_the_sweep_after_the_first_p_row(self):
        # The legal odd moves of {4,6,9} are 3, 5, 7, 11: {4,6,9}+5 is N and
        # {4,6,9,11} is P.
        native = self.run_solver('native_solver', 2, '--odd-list', '5,11,7', 4, 6, 9).splitlines()
        self.assertEqual([row.split()[1] for row in native], ['N', 'P', 'N'])
        for threads in (1, 2):
            rows = self.run_solver('parallel_solver', 2, '--threads', threads, '--stop-at-p',
                                   '--odd-list', '5,11,7', 4, 6, 9).splitlines()
            self.assertEqual([row.split()[:2] for row in rows], [['move=5', 'N'], ['move=11', 'P']])

    def test_kunz_keys_build_decides_like_native(self):
        # Roots whose smallest element is 2, 4, 8 or 16; with one thread the
        # output, state count included, is native_solver's.
        rng = random.Random(701)
        positions = [(2, 255), (4, 5, 6, 7, 17), (16, 26, 33, 62, 89, 102)]
        while len(positions) < 80:
            gens = sorted(rng.sample(range(3, 45), rng.randint(2, 5)))
            if gens[0] in (4, 8, 16) and reduce(gcd, gens) == 1 and frobenius_number(gens) <= 110:
                positions.append(tuple(gens))
        for index, gens in enumerate(positions):
            native = self.run_solver('native_solver', 4, *gens)
            exact = subprocess.run([str(self.kunz_keys), '--threads', '1', *map(str, gens)],
                                   capture_output=True, text=True, check=True).stdout
            self.assertEqual(exact, native, gens)
            threaded = subprocess.run([str(self.kunz_keys), '--threads', str(2 + index % 3), '--verify-memo',
                                       *map(str, gens)], capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(threaded[0], native.split()[0], gens)
            self.assertTrue(threaded[-1].startswith('entries='), gens)
        for args in (['--odd-range', 3, 31, 16, 26, 82, 88], ['--odd-range', 3, 41, 16, 26]):
            self.assertEqual(subprocess.run([str(self.kunz_keys), '--threads', '1', *map(str, args)],
                                            capture_output=True, text=True, check=True).stdout,
                             self.run_solver('native_solver', 4, *args), args)
        # Other smallest elements are outside this build.
        result = subprocess.run([str(self.kunz_keys), '5', '7'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Kunz keys need a smallest root element of 2, 4, 8 or 16', result.stderr)

    def test_rejects_bad_arguments(self):
        binary = str(self.binaries['parallel_solver', 2])
        for args in (['--threads', '0', '4', '5'], ['--threads', 'x', '4', '5'], ['--split-depth', '-1', '4', '5'],
                     ['--bogus', '1', '4', '5'], ['4', '6'], ['--threads', '2'], ['16', '26', '62', '95', '98', '102'],
                     ['--odd-range', '4', '9', '16', '26'], ['--odd-list', '9,10', '16', '26'], ['--odd-range', '5', '3', '16', '26'], ['4', '7', '--split-depth', '3'],
                     ['--threads', '2', '--split-depth', '0', '4', '5'], ['50000', '50001'], ['4', '5x'],
                     ['--odd-list', '3', '6', '9'], ['--threads'], ['--stop-at-p', '4', '5'],
                     ['--odd-list', '5,13', '4', '6', '9'], ['2000000000', '2000000001']):
            result = subprocess.run([binary, *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, args)
            self.assertEqual(result.stdout, '', args)
            self.assertTrue(result.stderr.startswith('parallel_solver: '), (args, result.stderr))


if __name__ == '__main__':
    unittest.main()
