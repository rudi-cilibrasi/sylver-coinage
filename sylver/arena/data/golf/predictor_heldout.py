"""Held-out measurements for a structural checking-cost predictor.

Usage: predictor_heldout.py HINT_FILE NATIVE_SOLVER OUT.jsonl

Seeded draw (random.Random(202609271)) of database N positions with a hinted
P child, Frobenius 120-200, not in the golf panel. For each: the verifier-
equivalent state counts of the root search and of the fewest-gaps hinted
witness child (fresh native solves), genus of both, and certificate bytes.
"""
import glob, json, os, random, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from concurrent.futures import ThreadPoolExecutor
from math import gcd
from functools import reduce
from sylver.arena.hints import Hints
from sylver.arena.common import position, key, canonical
from sylver.arena.golf import GOLF_PANEL, GOLF_RESEARCH
from sylver.solver import FiniteSolver, frobenius_number
HINTS, BIN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]  # hint file, native solver, output
f = HINTS; h = Hints(f, os.path.basename(f).split('.')[0])
panel = {k for _, k, _, _ in GOLF_PANEL + GOLF_RESEARCH}
genus = lambda p: len(FiniteSolver(p).gaps())
cands = []
for k, o in zip(h.keys, h.outcomes):
    if o != 'N' or k in panel: continue
    p = tuple(map(int, k.split(',')))
    if len(p) < 2 or reduce(gcd, p) != 1: continue
    F = frobenius_number(p)
    if 120 <= F < 200: cands.append(p)
random.Random(202609271).shuffle(cands)
def states(p, seconds=240):
    try:
        out = subprocess.run(['nice', '-n', '10', BIN, *map(str, p)], capture_output=True, text=True, timeout=seconds).stdout.split()
        return int(out[3].split('=')[1])
    except (subprocess.TimeoutExpired, IndexError):
        return None
chosen = []
for p in cands:
    s = FiniteSolver(p)
    wit = [(genus(c), frobenius_number(c), m, c) for m in s.legal_moves(s.initial_state)
           for c in [position((*p, m))] if h.get(c) == 'P']
    if wit: chosen.append((p, min(wit)))
    if len(chosen) >= 24: break
def measure(item):
    p, (g, F, m, c) = item
    root, child = states(p), states(c)
    leaf = {'schema': 1, 'root': key(p), 'nodes': {key(p): {'rule': 'finite', 'outcome': 'N'}}}
    edge = {'schema': 1, 'root': key(p), 'nodes': {key(p): {'rule': 'edge', 'outcome': 'N', 'move': m, 'child': key(c)},
                                                   key(c): {'rule': 'finite', 'outcome': 'P'}}}
    return {'target': key(p), 'root_states': root, 'root_genus': genus(p), 'root_F': frobenius_number(p),
            'witness': m, 'witness_states': child, 'witness_genus': g, 'witness_F': F,
            'C_leaf': len(canonical(leaf)), 'C_edge': len(canonical(edge))}
with ThreadPoolExecutor(2) as pool, open(OUT, 'w') as out:
    for row in pool.map(measure, chosen):
        out.write(json.dumps(row) + '\n'); out.flush()
