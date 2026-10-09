"""Least odd w (by the Frobenius number of C+w) with the finite C+w P, for a gcd-two position C.

Usage: witness.py [--wmax N] [--threads T] [--max-states S] GENERATOR...
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
import even_resolver  # noqa: E402
from sylver.arena.common import position  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('generators', nargs='+', type=int)
ap.add_argument('--wmax', type=int, default=401)
ap.add_argument('--batch', type=int, default=60)
ap.add_argument('--threads', type=int, default=2)
ap.add_argument('--max-states', type=int, default=300_000_000)
ap.add_argument('--timeout', type=int, default=3600)
a = ap.parse_args()
c = position(tuple(a.generators))
w, tried, states = even_resolver.odd_witness(c, a.wmax, a.batch, a.threads, a.max_states, a.timeout)
print(f'C={c} witness={w} tried={tried} states={states} skipped={even_resolver.SKIPPED}', flush=True)
