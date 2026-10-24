"""Screen even candidate answers a to the reply 40 after the opening 16 (discovery, not certified).

For a = 2 mod 4, {16,40,a} has gcd two and (for a > 2) a quiet-ender half, so by the Quiet End
Theorem it is P exactly when each obligation b (profile(...)['moves']) leads to an N-position.
Stage 1 (known): an obligation b whose child {16,40,a,b} is a known P-position refutes a. The list is
the reply-38 campaign's known_p.json plus the finite P-positions of the opening-16 table and ledger,
and the search-grade {16,38,72}; each refutation names its source.
Stage 2 (odd, with --odd): for each candidate stage 1 leaves, sweep its odd obligations (finite children)
with kunz in one shared memo, stopping at the first P: a P child refutes a.
Writes screen.jsonl (one row per candidate and stage).
Usage: screen.py [--odd [--p-table [--ncache-mb MB]] [--redo-partial]] [--amin A] [--amax A] [--threads T]
       [--max-states N] [--timeout S]
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/ruclaw/src/sylver-coinage')
KUNZ = HERE / 'kunz'
KUNZ_PT = HERE / 'kunz_pt'      # sylver/kunz_solver.cpp --p-table at e335ff0
KNOWN = json.loads((ROOT / 'sylver/campaigns/r38-2026-10-09/scan/known_p.json').read_text())
for p, why in [((2, 3), 'opening table'), ((5, 16, 18), 'opening table'), ((6, 7, 16), 'opening table'),
               ((9, 10, 16), 'opening table'), ((16, 23, 36), 'o16 ledger'), ((11, 16, 58), 'o16 ledger'),
               ((16, 37, 62), 'o16 ledger'), ((16, 33, 86), 'o16 ledger'), ((16, 17, 90), 'o16 ledger'),
               ((13, 16, 140), 'o16 ledger'), ((16, 21, 156), 'o16 ledger'), ((16, 31, 150), 'o16 scan (search)'),
               ((16, 38, 72), 'reply-38 search'),
               ((16, 20, 46), 'r40 search: P (pair_any_16-40-46-60.log)')]:
    KNOWN.setdefault(key(p), why)
OUT = HERE / 'screen.jsonl'


def candidates(amax):
    return [a for a in range(6, amax + 1, 4) if legal((16, 40), a)]


def known_refutation(base, moves):
    for b in moves:
        k = key(position((*base, b)))
        if k in KNOWN:
            return b, k, KNOWN[k]
    return None


def odd_sweep(base, odd, a_):
    engine = [str(KUNZ_PT), '--p-table', '--ncache-mb', str(a_.ncache_mb)] if a_.p_table else [str(KUNZ)]
    argv = [*engine, '--threads', str(a_.threads), '--stop-at-p', '--max-states', str(a_.max_states),
            '--odd-list', ','.join(map(str, odd)), *map(str, base)]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=a_.timeout)
        out, err, status = proc.stdout, proc.stderr, 'ok' if proc.returncode == 0 else f'exit {proc.returncode}'
    except subprocess.TimeoutExpired as e:
        out, err, status = (e.stdout or b'').decode(), '', 'timeout'
    rows = [l.split() for l in out.splitlines() if l.startswith('move=')]
    res = {int(r[0].split('=')[1]): (r[1], r[2].split('=')[1]) for r in rows}
    p = [m for m, (o, _) in res.items() if o == 'P']
    return {'classified': len(res), 'P_moves': p, 'complete': len(res) == len(odd) and not p,
            'status': status, 'stopped_early': 'sweep stopped' in err,
            'states': int(rows[-1][4].split('=')[1]) if rows else 0, 'seconds': round(time.monotonic() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--odd', action='store_true')
    ap.add_argument('--amax', type=int, default=398)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--max-states', type=int, default=200_000_000)
    ap.add_argument('--timeout', type=float, default=3600)
    ap.add_argument('--p-table', action='store_true', help='kunz_pt --p-table (the cap then counts P-positions)')
    ap.add_argument('--ncache-mb', type=int, default=8192)
    ap.add_argument('--amin', type=int, default=6)
    ap.add_argument('--redo-partial', action='store_true', help='sweep again candidates whose odd stage stopped early')
    a_ = ap.parse_args()
    done = {(r['a'], r['stage']) for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
    refuted = {r['a'] for r in map(json.loads, OUT.read_text().splitlines()) if r.get('refuted')} if OUT.exists() else set()
    partial = set()
    if OUT.exists():
        for r in map(json.loads, OUT.read_text().splitlines()):
            if r['stage'] == 'odd' and not r['refuted'] and not r['complete']:
                partial.add(r['a'])
    if a_.redo_partial:
        done -= {(a, 'odd') for a in partial}
    for a in [c for c in candidates(a_.amax) if c >= a_.amin]:
        base = position((16, 40, a))
        info = profile(base)
        assert info['complete'] and info['tail'] == 'quiet-end-v1', (a, info['tail'])
        moves = info['moves']
        rows = []
        if (a, 'known') not in done:
            hit = known_refutation(base, moves)
            rows.append({'a': a, 'stage': 'known', 'base': list(base), 'obligations': len(moves),
                         'refuted': bool(hit), 'by': hit[0] if hit else None,
                         'child': hit[1] if hit else None, 'source': hit[2] if hit else None})
            if hit:
                refuted.add(a)
        if a_.odd and a not in refuted and (a, 'odd') not in done:
            odd = [m for m in moves if m % 2]
            r = odd_sweep(base, odd, a_)
            rows.append({'a': a, 'stage': 'odd', 'base': list(base), 'odd_obligations': len(odd),
                         'refuted': bool(r['P_moves']), 'by': r['P_moves'][0] if r['P_moves'] else None, **r,
                         'engine': 'kunz_pt --p-table (e335ff0)' if a_.p_table else 'kunz (0668ae4)',
                         'max_states': a_.max_states, 'threads': a_.threads,
                         'ncache_mb': a_.ncache_mb if a_.p_table else None, 'timeout': a_.timeout})
        with OUT.open('a') as fh:
            for row in rows:
                fh.write(json.dumps(row) + '\n')
        for row in rows:
            print(a, row['stage'], 'REFUTED by %s (%s)' % (row['by'], row.get('source', 'odd child P'))
                  if row['refuted'] else ('ODD-COMPLETE' if row.get('complete') else 'open'),
                  row.get('classified', ''), row.get('seconds', ''), flush=True)


if __name__ == '__main__':
    main()
