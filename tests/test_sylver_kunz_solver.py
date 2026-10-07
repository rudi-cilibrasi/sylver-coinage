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
    """Random gcd-one positions whose smallest generator is at most 16 (the Kunz engine's modulus)."""
    rng = random.Random(seed)
    positions = []
    while len(positions) < count:
        gens = sorted(rng.sample(range(3, pool), rng.randint(2, 5)))
        if gens[0] <= 16 and reduce(gcd, gens) == 1 and frobenius_number(gens) <= max_frobenius:
            positions.append(gens)
    return positions


class KunzSolverTests(unittest.TestCase):
    """kunz_solver.cpp must decide every position exactly as native_solver.cpp does."""

    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if compiler is None:
            raise unittest.SkipTest('g++ is required')
        cls.tmp = tempfile.TemporaryDirectory()

        def build(name, *flags, label):
            binary = Path(cls.tmp.name) / label
            subprocess.run([compiler, '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror', '-pthread',
                            *flags, str(ROOT / 'sylver' / f'{name}.cpp'), '-o', str(binary)], check=True)
            return binary
        cls.native = {words: build('native_solver', f'-DSYLVER_NATIVE_WORDS={words}', label=f'native-{words}')
                      for words in (2, 4, 8)}
        cls.parallel = build('parallel_solver', '-DSYLVER_NATIVE_WORDS=4', label='parallel-4')
        cls.kunz = build('kunz_solver', label='kunz')
        # The SIMD byte shuffles that discovery builds use.
        cls.kunz_arch = build('kunz_solver', '-march=native', label='kunz-native-arch')
        # Deliberately broken builds that --verify-memo must reject: one never
        # tries move 7 (a missed child); one forges a root "winning" by naming
        # 1; three store a key that is not the Kunz vector of a semigroup
        # containing the root.
        cls.faulty = build('kunz_solver', '-DSYLVER_KUNZ_TEST_SKIP_MOVE=7', label='faulty')
        cls.forged = build('kunz_solver', '-DSYLVER_KUNZ_TEST_FORGE_MOVE_ONE', label='forged')
        cls.bad_keys = {mode: build('kunz_solver', f'-DSYLVER_KUNZ_TEST_FORGE_KEY={mode}', label=f'bad-key-{mode}')
                        for mode in (1, 2, 3)}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_binary(self, binary, *args):
        return subprocess.run([str(binary), *map(str, args)], capture_output=True, text=True, check=True).stdout

    def assert_decides_like_native(self, gens, *options, words=2):
        native = self.run_binary(self.native[words], *gens).split()
        kunz = self.run_binary(self.kunz, *options, *gens).split()
        self.assertEqual(kunz[0], native[0], (gens, options))   # outcome
        self.assertEqual(kunz[2], native[2], (gens, options))   # Frobenius number
        if kunz[0] == 'N':
            # Any winning move is a valid answer: its child must be P.
            move = int(kunz[1].split('=')[1])
            self.assertNotIn(move, gens)
            child = self.run_binary(self.native[words], *gens, move).split()
            self.assertEqual(child[0], 'P', (gens, move, options))
        else:
            self.assertEqual(kunz[1], 'winning_move=none')

    def test_one_thread_prints_exactly_what_native_prints(self):
        for gens in random_positions(20260927, 120, 100):
            self.assertEqual(self.run_binary(self.kunz, '--threads', 1, *gens),
                             self.run_binary(self.native[2], *gens), gens)
        # Moduli from 2 to 16, including a position whose other generators
        # exceed its Frobenius number.
        for gens in ((2, 3), (3, 7), (4, 7), (4, 5, 11), (5, 9, 11), (11, 13, 17, 19), (16, 26, 33, 62, 89),
                     (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31)):
            self.assertEqual(self.run_binary(self.kunz, '--threads', 1, *gens),
                             self.run_binary(self.native[4], *gens), gens)

    def test_native_arch_build_decides_like_native(self):
        for index, gens in enumerate(random_positions(77, 30, 120)):
            native = self.run_binary(self.native[2], *gens)
            self.assertEqual(self.run_binary(self.kunz_arch, '--threads', 1, *gens), native, gens)
            threaded = self.run_binary(self.kunz_arch, '--threads', 2 + index % 4, '--verify-memo', *gens).split()
            self.assertEqual(threaded[0], native.split()[0], gens)
            self.assertTrue(threaded[-1].startswith('entries='), gens)

    def test_many_threads_decide_every_position_like_native(self):
        for index, gens in enumerate(random_positions(9, 60, 110)):
            threads = (2, 3, 8)[index % 3]
            depth = (1, 3, 6, 40)[index % 4]
            self.assert_decides_like_native(gens, '--threads', threads, '--split-depth', depth)
            native = self.run_binary(self.native[2], *gens).split()
            if native[0] == 'N':
                # Random positions are mostly N; each N position plus its
                # winning move is a P position, where a missed child would
                # show up as a false N.
                child = sorted({*gens, int(native[1].split('=')[1])})
                self.assert_decides_like_native(child, '--threads', threads, '--split-depth', depth)

    def test_verify_memo_accepts_honest_searches(self):
        for index, gens in enumerate(random_positions(31, 40, 110)):
            threads = (1, 2, 4, 8)[index % 4]
            depth = (1, 3, 6, 40, 60)[index % 5]
            for args in (['--threads', threads, '--split-depth', depth, '--verify-memo', *gens],
                         ['--threads', threads, '--split-depth', depth, '--verify-memo', '--odd-range', 3, 21, 16, 26]):
                result = subprocess.run([str(self.kunz), *map(str, args)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, (args, result.stderr))
                *rows, last = result.stdout.splitlines()
                states = rows[-1].split()[-1].split('=')[1]
                self.assertEqual(last, f'verified entries={states}', args)
                self.assertEqual(result.stderr, f'kunz_solver: memo verified ({states} entries)\n', args)
                if index % 4:
                    break   # the sweep once per thread count is enough

    def assert_verification_fails(self, binary, args, reason):
        result = subprocess.run([str(binary), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, args)
        self.assertIn('memo verification failed: ' + reason, result.stderr, args)
        self.assertNotIn('verified', result.stdout, args)

    def test_verify_memo_rejects_a_search_that_misses_a_child(self):
        # {9,11,13} is P; the faulty build calls it N. {5,8} is N either way,
        # but the faulty memo still holds false P entries.
        for gens, outcome in (((9, 11, 13), 'P'), ((5, 8), 'N'), ((12, 15, 19), 'N')):
            self.assertEqual(self.run_binary(self.native[2], *gens).split()[0], outcome)
            for threads in (1, 3):
                self.assert_verification_fails(self.faulty, ['--threads', threads, '--verify-memo', *gens], '')

    def test_verify_memo_rejects_a_root_that_names_1(self):
        # Naming 1 reaches the semigroup of every integer, which has no moves;
        # an entry claiming that as a win must fail however it is presented.
        for gens in ((9, 11, 13), (5, 8)):
            for args in (['--threads', '2', '--verify-memo', *gens],
                         ['--threads', '1', '--verify-memo', '--odd-list', '3', '4', '6']):
                self.assert_verification_fails(self.forged, args, '')

    def test_verify_memo_rejects_keys_that_are_not_states(self):
        # Mode 1 sets residue 1's coordinate to 0 (1 would be an element but
        # 1 + 1 = 2 would not); mode 2 adds a gap the root does not have; mode
        # 3 sets the last lane, beyond every modulus below 16.
        reasons = {1: 'a key is not the Kunz vector of a semigroup', 2: "a key's state does not contain the root",
                   3: 'a key uses a lane beyond the modulus'}
        for mode, reason in reasons.items():
            for args in (['--threads', '1', '--verify-memo', 9, 11, 13], ['--threads', '3', '--verify-memo', 5, 8],
                         ['--threads', '2', '--verify-memo', '--odd-range', 3, 21, 12, 14]):
                self.assert_verification_fails(self.bad_keys[mode], args, reason)

    def test_repeated_runs_on_larger_positions(self):
        # Larger searches give threads time to interleave; every repetition
        # must reach the native outcome.
        for gens in random_positions(5, 6, 180, pool=60):
            for threads in (4, 8, 16):
                self.assert_decides_like_native(gens, '--threads', threads, words=4)

    def test_campaign_control(self):
        # {16,26,33,62,89,102} is P with exactly 1,721,485 states (PR #13).
        self.assertEqual(self.run_binary(self.kunz, '--threads', 1, 16, 26, 33, 62, 89, 102).strip(),
                         'P winning_move=none frobenius=119 states=1721485')
        for _ in range(3):
            out = self.run_binary(self.kunz, '--threads', 6, '--verify-memo', 16, 26, 33, 62, 89, 102).split()
            self.assertEqual(out[:3], ['P', 'winning_move=none', 'frobenius=119'])

    def test_sweeps_with_one_thread_print_exactly_what_native_and_parallel_print(self):
        for args in (['--odd-range', 3, 41, 16, 26], ['--odd-list', '45,9,31', 12, 20, 22],
                     ['--odd-range', 3, 29, 10, 14], ['--odd-range', 3, 31, 16, 26, 82, 88]):
            native = self.run_binary(self.native[4], *args)
            self.assertEqual(self.run_binary(self.kunz, '--threads', 1, *args), native, args)
            self.assertEqual(self.run_binary(self.parallel, '--threads', 1, *args), native, args)

    def test_sweep_with_threads_decides_every_row_like_native(self):
        for threads in (3, 8):
            rows = self.run_binary(self.kunz, '--threads', threads, '--odd-range', 3, 41, 16, 26).splitlines()
            self.assertEqual(len(rows), 20)
            for row in rows:
                move, outcome, winning, frobenius = row.split()[:4]
                move = move.split('=')[1]
                # Each row against a separate single-position native run.
                single = self.run_binary(self.native[4], 16, 26, move).split()
                self.assertEqual([outcome, frobenius], [single[0], single[2]], row)
                if outcome == 'N':   # a winning move of 16,26,move: its child must be P
                    child = self.run_binary(self.native[4], 16, 26, move, winning.split('=')[1])
                    self.assertEqual(child.split()[0], 'P', row)

    def test_stop_at_p_ends_the_sweep_after_the_first_p_row(self):
        # The legal odd moves of {4,6,9} are 3, 5, 7, 11: {4,6,9}+5 is N and
        # {4,6,9,11} is P.
        for threads in (1, 2):
            rows = self.run_binary(self.kunz, '--threads', threads, '--stop-at-p',
                                   '--odd-list', '5,11,7', 4, 6, 9).splitlines()
            self.assertEqual([row.split()[:2] for row in rows], [['move=5', 'N'], ['move=11', 'P']])

    def test_self_check(self):
        # The vector moves against the reference move and a bitset closure,
        # for every modulus from 2 to 16 up to the coordinate limit.
        for binary in (self.kunz, self.kunz_arch):
            out = self.run_binary(binary, '--self-check').split()
            self.assertEqual(out[:2], ['self-check', 'passed:'])
            self.assertGreater(int(out[2]), 10000)

    def test_positions_at_the_coordinate_limit(self):
        # {2,255} (F=253) and {3,191} (F=379) have a coordinate of 127, the
        # largest a key holds, and small game trees.
        for gens in ((2, 255), (2, 253), (3, 191), (3, 190, 191)):
            native = self.run_binary(self.native[8], *gens)
            self.assertEqual(self.run_binary(self.kunz, '--threads', 1, *gens), native, gens)
            self.assertEqual(self.run_binary(self.kunz_arch, '--threads', 1, *gens), native, gens)
            threaded = self.run_binary(self.kunz_arch, '--threads', 3, '--verify-memo', *gens).split()
            self.assertEqual(threaded[0], native.split()[0], gens)

    def test_max_states_and_stop_file_end_a_sweep_that_still_verifies(self):
        args = ['--odd-range', 3, 41, 16, 26, 82, 88]
        full = self.run_binary(self.kunz, '--threads', 1, *args).splitlines()
        for limit in (100, 5000, 200000):
            result = subprocess.run([str(self.kunz), '--threads', '1', '--verify-memo', '--max-states', str(limit),
                                     *map(str, args)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, (limit, result.stderr))
            *rows, last = result.stdout.splitlines()
            self.assertLess(len(rows), len(full), limit)
            self.assertEqual(rows, full[:len(rows)], limit)   # finished rows are the sweep's own rows
            self.assertIn('kunz_solver: sweep stopped', result.stderr, limit)
            self.assertTrue(last.startswith('verified entries='), limit)
        with tempfile.TemporaryDirectory() as tmp:
            stop = Path(tmp) / 'STOP'
            stop.write_text('')
            result = subprocess.run([str(self.kunz), '--threads', '2', '--verify-memo', '--stop-file', str(stop),
                                     *map(str, args)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = result.stdout.splitlines()
            self.assertEqual([row.split()[0] for row in rows[:-1]], ['move=3'])   # stops before the second row
            self.assertTrue(rows[-1].startswith('verified entries='))
            self.assertIn('sweep stopped before move=5 (stop file)', result.stderr)

    def test_memo_stats(self):
        result = subprocess.run([str(self.kunz), '--memo-stats', '--threads', '2', '16', '26', '33', '62', '89'],
                                capture_output=True, text=True, check=True)
        states = int(result.stdout.split()[-1].split('=')[1])
        line = result.stderr.strip().split()
        self.assertEqual(line[:2], ['kunz_solver:', 'memo'])
        stats = dict(item.split('=') for item in line[2:])
        self.assertEqual(int(stats['entries']), states)
        self.assertEqual(int(stats['bytes']), 17 * int(stats['slots']))
        # At most 7/8 of the slots are full; small shards may be far emptier.
        self.assertGreaterEqual(int(stats['slots']) * 7, states * 8)

    def test_rejects_bad_arguments(self):
        for args in (['--threads', '0', '4', '5'], ['--threads', 'x', '4', '5'], ['--split-depth', '-1', '4', '5'],
                     ['--bogus', '1', '4', '5'], ['4', '6'], ['--threads', '2'],
                     ['--odd-range', '4', '9', '16', '26'], ['--odd-list', '9,10', '16', '26'],
                     ['--odd-range', '5', '3', '16', '26'], ['4', '7', '--split-depth', '3'],
                     ['--threads', '2', '--split-depth', '0', '4', '5'], ['50000', '50001'], ['4', '5x'],
                     ['--odd-list', '3', '6', '9'], ['--threads'], ['--stop-at-p', '4', '5'],
                     ['--odd-list', '5,13', '4', '6', '9'], ['2000000000', '2000000001'],
                     # Outside the Kunz engine: a smallest generator above 16, and
                     # a bound whose coordinates exceed 127 (3 * 127 < 1997).
                     ['17', '19'], ['3', '1000'], ['--odd-range', '3', '9', '18', '20'],
                     ['--max-states', ' -1', '--odd-list', '5', '4', '6', '9'],
                     ['--max-states', '0', '--odd-list', '5', '4', '6', '9'],
                     ['--max-states', '12x', '--odd-list', '5', '4', '6', '9'], ['--max-states', '100', '4', '5'],
                     ['--stop-file', 'STOP', '4', '5'], ['--self-check', '4', '5']):
            result = subprocess.run([str(self.kunz), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, args)
            self.assertEqual(result.stdout, '', args)
            self.assertTrue(result.stderr.startswith('kunz_solver: '), (args, result.stderr))


if __name__ == '__main__':
    unittest.main()
