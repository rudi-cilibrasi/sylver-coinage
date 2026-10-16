"""Replay recorded kunz results with kunz_p: the outcome and the (least) winning move must agree."""
import json, random, subprocess, sys, time
from pathlib import Path
K = Path(__file__).resolve().parent
S = Path(sys.argv[1])
rows = [json.loads(l) for l in open(S / 'hunt.jsonl')] + [json.loads(l) for l in open(S / 'hard_queue.jsonl')]
solved = [r for r in rows if r.get('states') and r['outcome'] in ('N', 'P')]
random.seed(20261014)
small_n = random.sample([r for r in solved if r['outcome'] == 'N' and r['states'] < 400_000_000], 12)
ps = [r for r in solved if r['outcome'] == 'P' and r['states'] < 400_000_000]
cases = ps + small_n
bad = 0
for r in cases:
    t0 = time.monotonic()
    out = subprocess.run([str(K / 'kunz_p'), '--threads', '8', '--stop-at-p', '--ncache-mb', '2048',
                          '--odd-list', str(r['w']), *map(str, r['child'])], capture_output=True, text=True).stdout
    row = next(l.split() for l in out.splitlines() if l.startswith('move='))
    got = (row[1], row[2].split('=')[1])
    want = (r['outcome'], 'none' if r['outcome'] == 'P' else str(r['winning_move']))
    ok = got == want
    bad += not ok
    print('ok ' if ok else 'BAD', r['child'], r['w'], 'want', want, 'got', got, 'P-table', row[4].split('=')[1],
          'vs states', r['states'], f'{time.monotonic() - t0:.0f}s', flush=True)
print('mismatches:', bad, 'of', len(cases))
