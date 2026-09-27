#!/usr/bin/env python3
"""Structural audit of the W odd-reply scan ledger (separate from replay).

Checks every row's canonical position, Frobenius number, and, for N rows,
that the reported winning move is legal. Derives each branch's classified
odd replies and its first unclassified odd reply. Exact outcomes are the
scan's native results; only the P rows have independent replays.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from sylver.short_certificates import is_generated, minimal_generators
from sylver.solver import frobenius_number

W = (16, 26, 62, 98)
MOVES = (70, 86, 92, 108, 118)


def main():
    rows = [json.loads(line) for line in (HERE / 'scan/ledger.jsonl').read_text().splitlines()]
    known = json.loads((HERE / 'scan/prior-classified.json').read_text())
    report = {'rows': len(rows), 'branches': {}, 'failures': []}
    for row in rows:
        p = minimal_generators((*W, row['m'], row['r']))
        if list(p) != row['position'] or frobenius_number(p) != row['frobenius']:
            report['failures'].append({'row': row, 'error': 'position or Frobenius mismatch'})
        if row['status'] == 'ok' and row['outcome'] == 'N':
            w = row['winning_move']
            if w is None or w < 2 or is_generated(p, w):
                report['failures'].append({'row': row, 'error': 'illegal winning move'})
    for m in MOVES:
        mine = [r for r in rows if r['m'] == m and r['status'] == 'ok']
        n = sorted(r['r'] for r in mine if r['outcome'] == 'N')
        p = sorted(r['r'] for r in mine if r['outcome'] == 'P')
        # A P row counts as a refutation only with a certificate and a verified
        # independent replay receipt in this campaign directory.
        verified = [r for r in p if (HERE / f'w{m}-certificate.json').exists() and
                    json.loads((HERE / f'w{m}-certificate.json').read_text())['reply'] == r and
                    (HERE / f'verification/w{m}/receipt.json').exists() and
                    json.loads((HERE / f'verification/w{m}/receipt.json').read_text())['status'] == 'verified']
        classified = set(n) | set(p) | set(known[str(m)])
        first = next(r for r in range(3, 10000, 2) if r not in classified)
        report['branches'][str(m)] = {'scan_N': len(n), 'scan_P': p, 'verified_P': verified,
                                      'pending_replay_P': sorted(set(p) - set(verified)),
                                      'prior_classified': len(known[str(m)]),
                                      'first_unclassified_odd_reply': None if verified else first,
                                      'scan_max_reply': max((r['r'] for r in mine), default=None)}
    print(json.dumps(report, indent=2))
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
