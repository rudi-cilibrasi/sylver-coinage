import random
import shutil
import subprocess
import tempfile
import unittest
from math import gcd
from functools import reduce
from pathlib import Path

from sylver.solver import frobenius_number

ROOT = Path(__file__).resolve().parents[1]


class FastSolverDifferentialTests(unittest.TestCase):
    """fast_solver.cpp must print exactly what native_solver.cpp prints."""

    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if compiler is None:
            raise unittest.SkipTest('g++ is required')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binaries = {}
        for name in ('native_solver', 'fast_solver'):
            for words in (2, 4):
                binary = Path(cls.tmp.name) / f'{name}-{words}'
                subprocess.run([compiler, '-std=c++20', '-O3', '-Wall', '-Wextra', '-pedantic', '-Werror',
                                f'-DSYLVER_NATIVE_WORDS={words}', str(ROOT / 'sylver' / f'{name}.cpp'),
                                '-o', str(binary)], check=True)
                cls.binaries[name, words] = binary

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def both(self, words, *args):
        outs = [subprocess.run([str(self.binaries[name, words]), *args], capture_output=True, text=True, check=True).stdout
                for name in ('native_solver', 'fast_solver')]
        self.assertEqual(outs[0], outs[1], args)
        return outs[0]

    def test_random_positions_match_exactly(self):
        rng = random.Random(20260927)
        checked = 0
        while checked < 150:
            gens = sorted(rng.sample(range(3, 45), rng.randint(2, 5)))
            if reduce(gcd, gens) != 1 or frobenius_number(gens) > 100:
                continue
            self.both(2, *map(str, gens))
            checked += 1

    def test_batch_and_hints_modes_match(self):
        rng = random.Random(7)
        rows = []
        while len(rows) < 40:
            gens = sorted(rng.sample(range(4, 40), rng.randint(2, 4)))
            if reduce(gcd, gens) == 1 and frobenius_number(gens) <= 127:
                rows.append(','.join(map(str, gens)))
        with tempfile.TemporaryDirectory() as d:
            batch = Path(d) / 'batch.txt'
            batch.write_text('\n'.join(rows) + '\n')
            out = self.both(2, '--batch-file', str(batch))
            self.assertEqual(len(out.splitlines()), 40)
            self.both(2, '--hints', '9,11,13', '--batch-file', str(batch))
        self.both(4, '--odd-range', '3', '41', '16', '26')

    def test_campaign_control(self):
        # {16,26,33,62,89,102} is P with exactly 1,721,485 states (PR #13).
        out = self.both(4, '16', '26', '33', '62', '89', '102')
        self.assertEqual(out.strip(), 'P winning_move=none frobenius=119 states=1721485')
