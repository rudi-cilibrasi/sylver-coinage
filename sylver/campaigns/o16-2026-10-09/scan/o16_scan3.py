"""A third round of the opening-16 rescan: named replies, resumed where o16_scan2 stopped, with longer limits.

o16_scan2.py (October 14 and 18-20) gave each stopped sweep 45 minutes. This resumes the replies named
on the command line at the candidate that sweep was on when its time ran out (the ledger's swept count
plus the candidates o16_scan2.jsonl classified), in the same order, and writes o16_scan3.jsonl.

The earlier notes follow.

The ledger's scan (sylver/campaigns/o16-2026-10-09/scan/finite_answers.py) swept, for each even
reply r, the odd gaps m of the reduced pair {16/d, r/d} (d = gcd(16, r)) legal after {16, r}, in
increasing order of the Frobenius number of {16, r, m}, in one shared memo, and stopped at the
first P or at an 800,000,000-state memo. Here each reply whose sweep stopped at that cap resumes
at the candidate in progress, with the P-table engine (one shared P-table and N-cache per reply)
and a time limit. Rows stream to o16_scan2.jsonl as kunz prints them, so a reply stopped by the
time limit keeps what it classified. A P row means {16, r, m} is P: m answers r.

Usage: o16_scan2.py [--threads T] [--ncache-mb MB] [--max-states P] [--timeout S] [R ...]
"""
import argparse, json, subprocess, sys, tempfile, threading, time
from math import gcd
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
LEDGER = Path('/home/ruclaw/src/sylver-coinage/sylver/campaigns/o16-2026-10-09/scan/finite_answers.jsonl')
OUT = HERE / 'o16_scan3.jsonl'
SCAN2 = {row['r']: row for row in map(json.loads, (HERE / 'o16_scan2.jsonl').read_text().splitlines())}
ap = argparse.ArgumentParser()
ap.add_argument('replies', nargs='*', type=int)
ap.add_argument('--threads', type=int, default=4)
ap.add_argument('--ncache-mb', type=int, default=8192)
ap.add_argument('--max-states', type=int, default=400_000_000)
ap.add_argument('--timeout', type=float, default=10800)
a = ap.parse_args()


def odd_gaps(p, q):
    limit = p * q
    reach = [True] + [False] * limit
    for n in range(1, limit + 1):
        reach[n] = (n >= p and reach[n - p]) or (n >= q and reach[n - q])
    return [n for n in range(3, limit + 1, 2) if not reach[n]]


def candidates(r):
    d = gcd(16, r)
    p, q = 16 // d, r // d
    cands = [m for m in odd_gaps(p, q) if legal((16, r), m)] if p > 1 and q > 1 else []
    return sorted(cands, key=lambda m: (frobenius_number(position((16, r, m))), m))


ledger = {row['r']: row for row in map(json.loads, LEDGER.read_text().splitlines())}
done = {row['r'] for row in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else set()
todo = a.replies or [r for r, row in sorted(ledger.items())
                     if row['answer'] is None and row.get('swept') is not None and row['swept'] < row['candidates']
                     and r != 38]                  # 38 has its own campaign (r38-2026-10-09)
for r in todo:
    if r in done:
        continue
    cands = candidates(r)
    swept = ledger[r]['swept']
    assert len(cands) == ledger[r]['candidates'], (r, len(cands), ledger[r]['candidates'])
    swept += len(SCAN2[r]['rows'])                # and the candidates o16_scan2 classified
    rest = cands[swept:]                          # from the candidate o16_scan2's sweep stopped in
    argv = ['/tmp/claude-1001/-home-ruclaw-src-sylver-coinage/cd9b0cdd-5710-4000-902b-0c5c9cdc90cc/scratchpad/r38/kunz_pt',
            '--p-table', '--ncache-mb', str(a.ncache_mb), '--threads', str(a.threads), '--stop-at-p',
            '--max-states', str(a.max_states), '--odd-list', ','.join(map(str, rest)), '16', str(r)]
    t0 = time.monotonic()
    rows, timed_out = [], False
    with tempfile.TemporaryFile('w+') as err:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=err, text=True)

        def read():                               # every row, as kunz flushes it
            for line in proc.stdout:
                if line.startswith('move='):
                    f = line.split()
                    rows.append([int(f[0].split('=')[1]), f[1],
                                 None if f[2].endswith('none') else int(f[2].split('=')[1]), int(f[4].split('=')[1])])
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            timed_out = True
        reader.join(timeout=30)                   # the pipe has closed: the reader drains it and ends
        err.seek(0)
        tail = err.read()[-300:]
    answer = next((m for m, o, _, _ in rows if o == 'P'), None)
    rec = {'r': r, 'resumed_at': swept, 'candidates': len(cands), 'tried': rest[:len(rows) + 1],
           'rows': rows, 'answer': answer, 'timed_out': timed_out, 'returncode': proc.returncode,
           'stderr_tail': tail, 'seconds': round(time.monotonic() - t0, 1),
           'engine': 'kunz_solver --p-table (e335ff0)', 'max_states': a.max_states, 'timeout': a.timeout,
           'threads': a.threads, 'ncache_mb': a.ncache_mb}
    with OUT.open('a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(time.strftime('%H:%M:%S'), f'r={r}: {len(rows)} more classified of {len(rest)}, answer {answer}, '
          f'{"timed out" if timed_out else "stopped" if not answer and len(rows) < len(rest) else "done"}, '
          f'{rec["seconds"]:.0f}s', flush=True)
