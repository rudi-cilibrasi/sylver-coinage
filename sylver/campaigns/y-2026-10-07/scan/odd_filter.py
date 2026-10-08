"""Odd-obligation filter for short candidate answers r to {16,28}.

For each r = 2 (mod 4) whose {16,28,r} is short, sweep its odd obligations
{16,28,r,m} (finite, gcd one) with kunz_solver in one shared memo and stop at
the first P: a P odd obligation means m wins from {16,28,r}, so r cannot
answer 28. Candidates with every odd obligation N are "odd-complete".
Appends one JSON line per candidate to odd_filter.jsonl.
"""
import json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import position, profile  # noqa: E402

HERE = Path(__file__).resolve().parent
ENGINE = HERE / 'kunz'
OUT = HERE / 'odd_filter.jsonl'


def main(rs, threads=10, max_states=900_000_000, timeout=3600):
    done = {json.loads(l)['r'] for l in OUT.read_text().splitlines()} if OUT.exists() else set()
    for r in rs:
        if r in done:
            continue
        base = position((16, 28, r))
        info = profile(base)
        if not (info['complete'] and info['tail'] == 'quiet-end-v1'):
            continue
        odd = [m for m in info['moves'] if m % 2]
        argv = [str(ENGINE), '--threads', str(threads), '--stop-at-p', '--max-states', str(max_states),
                '--odd-list', ','.join(map(str, odd)), *map(str, base)]
        start = time.monotonic()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            rows = [line.split() for line in proc.stdout.splitlines() if line.startswith('move=')]
            status = 'ok' if proc.returncode == 0 else f'exit {proc.returncode}'
            stopped = 'sweep stopped' in proc.stderr
        except subprocess.TimeoutExpired as error:
            rows = [line.split() for line in (error.stdout or b'').decode().splitlines() if line.startswith('move=')]
            status, stopped = 'timeout', True
        results = {int(row[0].split('=')[1]): row[1] for row in rows}
        p_moves = [m for m, o in results.items() if o == 'P']
        record = {'r': r, 'base': list(base), 'odd_obligations': odd, 'classified': len(results),
                  'P_moves': p_moves, 'complete': len(results) == len(odd) and not p_moves,
                  'status': status, 'stopped_early': stopped,
                  'states': int(rows[-1][4].split('=')[1]) if rows else 0,
                  'seconds': round(time.monotonic() - start, 1)}
        with OUT.open('a') as fh:
            fh.write(json.dumps(record) + '\n')
        verdict = 'REFUTED by ' + str(p_moves[0]) if p_moves else ('ODD-COMPLETE' if record['complete'] else 'partial')
        print(f"r={r:4} odd={len(odd):3} classified={len(results):3} {verdict:16} states={record['states']:>12,} "
              f"{record['seconds']:>8.1f}s {status}", flush=True)


if __name__ == '__main__':
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    main([r for r in range(lo, hi + 1, 4) if r % 4 == 2])
