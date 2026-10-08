"""Smaller finite witnesses for A={16,30,56}'s costliest obligations.

For each obligation m, sweep every legal odd reply w <= --wmax to A+m in one
shared memo (no stop at P), collect the P rows, then solve the smallest-Frobenius
P destinations alone, sequentially, and report their exact state counts.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

A = (16, 30, 56)


def main(moves, wmax=601, keep=6):
    report = {}
    for m in moves:
        child = position((*A, m))
        odd = sorted((w for w in range(3, wmax + 1, 2) if legal(child, w)),
                     key=lambda w: (frobenius_number(position((*child, w))), w))
        out = subprocess.run([str(HERE / 'kunz'), '--threads', '8', '--max-states', '1100000000',
                              '--odd-list', ','.join(map(str, odd)), *map(str, child)],
                             capture_output=True, text=True).stdout
        rows = [line.split() for line in out.splitlines() if line.startswith('move=')]
        ps = [int(r[0].split('=')[1]) for r in rows if r[1] == 'P']
        sizes = {}
        for w in ps[:keep]:
            line = subprocess.run([str(HERE / 'kunz'), '--threads', '1', *map(str, position((*child, w)))],
                                  capture_output=True, text=True, check=True).stdout.split()
            sizes[w] = int(line[3].split('=')[1])
        report[m] = {'child': list(child), 'swept': len(rows), 'P_replies': ps, 'sizes': sizes}
        print(m, 'swept', len(rows), 'P replies', ps[:12], 'sizes', sizes, flush=True)
    (HERE / 'alt_witness.json').write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main([int(x) for x in sys.argv[1:]])
