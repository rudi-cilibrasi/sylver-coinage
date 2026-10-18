#!/usr/bin/env python3
"""Write a finite-witness certificate for each distinct destination of {16,38,72}'s finite routes.

The reply-38 search recorded, for each obligation m of {16,38,72} that a finite reply answers, the
reply v (odd obligations: ../r38-2026-10-09/scan/odd72_all.out; even ones: even_72.jsonl, whose
"finite odd witness" rows give v, and the deeper sweeps deep_16-38-58-72 and deep_16-38-66-72).
Each route reaches a finite destination {16,38,72,m,v}. Partner routes often share one (69 -> 66 and
66 -> 69 both reach {16,38,66,69,72}), so this writes one certificate per destination, named after
the first obligation that reaches it, and audit.py checks every other route against it.
Usage: python make_certificates.py (writes c72_<m>-certificate.json, refusing to change one).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCAN = ROOT / 'sylver/campaigns/r38-2026-10-09/scan'
sys.path.insert(0, str(ROOT))
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

PARENT = (16, 38, 72)


def finite_routes():
    """{obligation m: reply v} for every recorded finite route of {16,38,72}, odd obligations first."""
    routes = {}
    for line in (SCAN / 'odd72_all.out').read_text().splitlines():
        m = re.match(r'move=(\d+) N winning_move=(\d+) ', line)
        if m:
            routes[int(m[1])] = int(m[2])
    for line in (SCAN / 'even_72.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['status'] == 'resolved' and row['via'] == 'finite odd witness':
            routes[row['e']] = row['reply']
    for e in (58, 66):
        rows = [json.loads(l) for l in (SCAN / f'deep_16-38-{e}-72.jsonl').read_text().splitlines()]
        routes[e] = int(next(r['P'] for r in rows if r.get('P')))
    return routes


def main():
    seen = {}
    for m, v in finite_routes().items():
        assert legal(PARENT, m) and legal(position((*PARENT, m)), v), (m, v)
        dest = position((*PARENT, m, v))
        if dest in seen:
            continue
        seen[dest] = m
        cert = {'schema': 1, 'parent': list(PARENT), 'opponent_move': m, 'reply': v, 'destination': list(dest),
                'destination_outcome': 'P', 'frobenius': frobenius_number(dest),
                'consequence': f'{{16,38,72}}+{m} is N by reply {v}.',
                'scope': 'Finite exhaustive-evaluation certificate. Replaying the destination requires no '
                         'inherited outcome cache, infinite-position certificate, or Quiet End Theorem.'}
        path = HERE / f'c72_{m}-certificate.json'
        text = json.dumps(cert, indent=2) + '\n'
        if path.exists() and path.read_text() != text:
            raise SystemExit(f'{path.name} exists with other content')
        path.write_text(text)
    print(len(seen), 'certificates')


if __name__ == '__main__':
    main()
