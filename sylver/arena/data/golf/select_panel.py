#!/usr/bin/env python3
"""Reproduce the golf panel's two predeclared, seeded draws.

Draw 1 (``random``) took N and P targets at random per Frobenius band from
the 305,011-row cache; only 3 of its 8 N targets had any hinted P child,
because the database records outcomes, not winning moves. Draw 2
(``witnessed``) took N targets among database N positions with at least one
hinted P child. Its tier A and B N targets and draw 1's P targets form
``GOLF_PANEL`` in ``sylver/arena/golf.py``. Acceptance used the native
solver's deterministic evaluated-state count, never timing: tier A at most
2M states, tier B 0.5M-8M; oversized or over-time candidates were skipped.

    python sylver/arena/data/golf/select_panel.py NATIVE_SOLVER HINT_FILE OUT.jsonl

HINT_FILE is ``fixtures/visible/hints/aa421ec0...txt.gz`` from the archive
(or rebuild it with ``python -m sylver.arena fixtures --golf``). Rows are
appended to OUT.jsonl in the order they were measured.
"""
from functools import reduce
import json
from math import gcd
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from sylver.arena.common import position
from sylver.arena.hints import Hints
from sylver.solver import FiniteSolver, frobenius_number

BANDS = {'A': (100, 150, 0, 2_000_000), 'B': (150, 200, 500_000, 8_000_000)}


def states(binary, p, seconds):
    try:
        out = subprocess.run([binary, *map(str, p)], capture_output=True, text=True, timeout=seconds).stdout.split()
    except subprocess.TimeoutExpired:
        return None
    return out[0], int(out[3].split('=')[1])


def draw_random(binary, out):
    rows = sorted((k, 'P' if v == '1' else 'N') for k, v in
                  (line.split() for line in open(ROOT / 'sylver/move26_data/periodicity_x.cache')))
    rng = random.Random(20260927)
    cand = {(b, o): [] for b in BANDS for o in 'PN'}
    for k, o in rows:
        g = tuple(map(int, k.split(',')))
        if len(g) < 2 or reduce(gcd, g) != 1:
            continue
        f = frobenius_number(g)
        for b, (lo, hi, _, _) in BANDS.items():
            if lo <= f < hi:
                cand[(b, o)].append((k, f))
    for v in cand.values():
        rng.shuffle(v)
    for (b, o), items in sorted(cand.items()):
        got = 0
        for k, f in items:
            if got >= 3:
                break
            r = states(binary, k.split(','), 240)
            if r is None:
                continue
            ok = BANDS[b][2] <= r[1] <= BANDS[b][3]
            out.write(json.dumps({'draw': 'random', 'tier': b, 'outcome': o, 'target': k, 'F': f,
                                  'states': r[1], 'accepted': ok}) + '\n')
            got += ok


def draw_witnessed(binary, hints, out):
    rng = random.Random(20260927)
    cands = {b: [] for b in BANDS}
    for k, o in zip(hints.keys, hints.outcomes):
        p = tuple(map(int, k.split(',')))
        if o != 'N' or len(p) < 2 or reduce(gcd, p) != 1:
            continue
        f = frobenius_number(p)
        for b, (lo, hi, _, _) in BANDS.items():
            if lo <= f < hi:
                cands[b].append((k, f))
    for b, items in cands.items():
        rng.shuffle(items)
        got = 0
        for k, f in items:
            if got >= 3:
                break
            p = tuple(map(int, k.split(',')))
            s = FiniteSolver(p)
            witnesses = [m for m in s.legal_moves(s.initial_state) if hints.get(position((*p, m))) == 'P']
            if not witnesses:
                continue
            r = states(binary, p, 300)
            if r is None:
                continue
            ok = BANDS[b][2] <= r[1] <= BANDS[b][3]
            out.write(json.dumps({'draw': 'witnessed', 'tier': b, 'outcome': 'N', 'target': k, 'F': f,
                                  'states': r[1], 'witnesses': witnesses, 'accepted': ok}) + '\n')
            got += ok


if __name__ == '__main__':
    binary, hint_file, target = sys.argv[1:4]
    hints = Hints(hint_file, Path(hint_file).name.split('.')[0])
    with open(target, 'a') as out:
        draw_random(binary, out)
        draw_witnessed(binary, hints, out)
