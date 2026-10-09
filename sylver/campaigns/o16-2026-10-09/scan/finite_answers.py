"""Finite odd answers to replies r after the opening 16.

For each legal reply r (r not a multiple of 16), d = gcd(16, r) and the reduced
pair {16/d, r/d}; sweep the odd gaps m > 1 of <16/d, r/d> with kunz_solver
(one shared memo per r, stopping at the first P). A P row means {16,r,m} is a
finite P-position: m answers r. Finding none does not show r has no answer.
"""
import json, subprocess, sys
from math import gcd
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position
from sylver.solver import frobenius_number

HERE = Path(__file__).resolve().parent

def odd_gaps(a, b):
    limit = a * b
    reach = [True] + [False] * limit
    for n in range(1, limit + 1):
        reach[n] = (n >= a and reach[n - a]) or (n >= b and reach[n - b])
    return [n for n in range(3, limit + 1, 2) if not reach[n]]

def main(lo, hi):
    out = HERE / 'finite_answers.jsonl'
    for r in range(lo, hi + 1, 2):
        if r % 16 == 0:
            continue
        d = gcd(16, r)
        a, b = 16 // d, r // d
        cands = [m for m in odd_gaps(a, b) if legal((16, r), m)] if a > 1 and b > 1 else []
        cands.sort(key=lambda m: (frobenius_number(position((16, r, m))), m))
        row = {'r': r, 'd': d, 'candidates': len(cands), 'answer': None}
        if cands:
            proc = subprocess.run([str(HERE / 'kunz'), '--threads', '8', '--stop-at-p', '--max-states', '800000000',
                                   '--odd-list', ','.join(map(str, cands)), '16', str(r)],
                                  capture_output=True, text=True, timeout=7200)
            rows = [l.split() for l in proc.stdout.splitlines() if l.startswith('move=')]
            p = [int(x[0].split('=')[1]) for x in rows if x[1] == 'P']
            row.update(swept=len(rows), answer=p[0] if p else None, returncode=proc.returncode)
        with out.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
