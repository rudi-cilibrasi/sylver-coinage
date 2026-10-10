"""Deep odd-witness sweep of one gcd-two position C: the least odd w (by C+w's Frobenius number) with C+w P.

Usage: deep_witness.py [--after N | --done-count K] [--also W,W,...] [--wmax M] [--batch B] [--threads T]
                       [--max-states S] [--max-skips K] GENERATOR...
Sweeps the odd w > N (and the --also list, replies an earlier sweep skipped) in
batches sharing one memo, stopping at the first P. A batch that hits the state cap
skips the reply in progress and requeues the rest. Appends one JSON line per batch
to deep_<C>.jsonl and prints the result.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('generators', nargs='+', type=int)
ap.add_argument('--after', type=int, default=1)
ap.add_argument('--done-count', type=int, default=0,
                help="skip the first K replies of a resolver's order (odd w <= 401 by Frobenius number); "
                     "--also brings back the ones it skipped")
ap.add_argument('--also', default='')
ap.add_argument('--wmax', type=int, default=801)
ap.add_argument('--batch', type=int, default=30)
ap.add_argument('--threads', type=int, default=4)
ap.add_argument('--max-states', type=int, default=1_000_000_000)
ap.add_argument('--max-skips', type=int, default=8)
a = ap.parse_args()
c = position(tuple(a.generators))
also = [int(x) for x in a.also.split(',') if x]
order = lambda w: (frobenius_number(position((*c, w))), w)
done = set(sorted((w for w in range(3, 402, 2) if legal(c, w)), key=order)[:a.done_count]) - set(also)
odd = sorted({w for w in range(a.after + 1 + (a.after % 2 == 1), a.wmax + 1, 2) if legal(c, w)} - done | set(also),
             key=order)
log = HERE / f"deep_{key(c).replace(',', '-')}.jsonl"
queue, skipped, n = list(odd), [], 0
print(time.strftime('%H:%M:%S'), 'C =', c, 'candidates', len(queue), 'first', queue[:8], flush=True)
while queue:
    chunk, queue = queue[:a.batch], queue[a.batch:]
    start = time.monotonic()
    argv = [str(HERE / 'kunz'), '--threads', str(a.threads), '--stop-at-p', '--max-states', str(a.max_states),
            '--odd-list', ','.join(map(str, chunk)), *map(str, c)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    rows = [l.split() for l in proc.stdout.splitlines() if l.startswith('move=')]
    n += len(rows)
    hit = next((int(r[0].split('=')[1]) for r in rows if r[1] == 'P'), None)
    rec = {'chunk': chunk, 'classified': [int(r[0].split('=')[1]) for r in rows], 'P': hit,
           'returncode': proc.returncode, 'stderr_tail': proc.stderr[-300:], 'seconds': round(time.monotonic() - start, 1)}
    with log.open('a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(time.strftime('%H:%M:%S'), f'batch {chunk[0]}..{chunk[-1]}: classified {len(rows)}/{len(chunk)}, P={hit}, '
          f'{rec["seconds"]}s', flush=True)
    if hit:
        print('WITNESS', hit, 'classified', n, 'skipped', skipped, flush=True)
        break
    if len(rows) < len(chunk):
        skipped.append(chunk[len(rows)])
        queue = chunk[len(rows) + 1:] + queue
        if len(skipped) >= a.max_skips:
            print('GAVE UP after', n, 'classified; skipped', skipped, flush=True)
            break
else:
    print('NO WITNESS up to', a.wmax, 'classified', n, 'skipped', skipped, flush=True)
