"""Deep odd-witness sweep of one gcd-two position C: the least odd w (by C+w's Frobenius number) with C+w P.

Usage: deep_witness.py [--after N | --done-count K] [--also W,W,...] [--exclude W,W,...] [--wmax M] [--batch B]
                       [--threads T] [--max-states S] [--max-skips K] GENERATOR...
Sweeps the odd w > N (and the --also list, replies an earlier sweep skipped) in
batches sharing one memo, leaving out the --exclude list (replies an earlier sweep classified), stopping at the first P. A batch that hits the state cap
skips the reply in progress and requeues the rest. Appends one JSON line per batch
to deep_<C>.jsonl and prints the result. A SIGTERM (as from timeout) stops the sweep after
recording the replies the batch in progress had classified, with returncode "timeout".
"""
import argparse, json, signal, subprocess, sys, tempfile, time
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
ap.add_argument('--exclude', default='', help='replies already classified (N) by an earlier sweep')
ap.add_argument('--wmax', type=int, default=801)
ap.add_argument('--batch', type=int, default=30)
ap.add_argument('--threads', type=int, default=4)
ap.add_argument('--max-states', type=int, default=1_000_000_000)
ap.add_argument('--max-skips', type=int, default=8)
a = ap.parse_args()
c = position(tuple(a.generators))
also = [int(x) for x in a.also.split(',') if x]
exclude = {int(x) for x in a.exclude.split(',') if x}
order = lambda w: (frobenius_number(position((*c, w))), w)
done = set(sorted((w for w in range(3, 402, 2) if legal(c, w)), key=order)[:a.done_count]) - set(also)
odd = sorted(({w for w in range(a.after + 1 + (a.after % 2 == 1), a.wmax + 1, 2) if legal(c, w)} - done | set(also)) - exclude,
             key=order)
log = HERE / f"deep_{key(c).replace(',', '-')}.jsonl"
queue, skipped, n = list(odd), [], 0


class Stop(Exception):
    pass


stopping = reading = False


def on_term(signum, frame):
    global stopping
    stopping = True
    if reading:                 # interrupt the read; otherwise let the record being written finish
        raise Stop


signal.signal(signal.SIGTERM, on_term)


def run_batch(chunk):
    """Run kunz on one batch, keeping the replies it classifies even if a signal stops it part way."""
    global reading
    argv = [str(HERE / 'kunz'), '--threads', str(a.threads), '--stop-at-p', '--max-states', str(a.max_states),
            '--odd-list', ','.join(map(str, chunk)), *map(str, c)]
    rows = []
    with tempfile.TemporaryFile('w+') as err:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=err, text=True)
        reading = True
        try:
            for line in proc.stdout:
                if line.startswith('move='):
                    rows.append(line.split())
            rc = proc.wait()
        except Stop:
            rc = 'timeout'
        finally:
            reading = False
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        try:
            for line in proc.stdout:    # rows already in the pipe when the signal came
                if line.startswith('move='):
                    rows.append(line.split())
        except (OSError, ValueError):
            pass
        err.seek(0)
        return rows, rc, err.read()[-300:]


print(time.strftime('%H:%M:%S'), 'C =', c, 'candidates', len(queue), 'first', queue[:8], flush=True)
while queue:
    chunk, queue = queue[:a.batch], queue[a.batch:]
    start = time.monotonic()
    rows, rc, tail = run_batch(chunk)
    n += len(rows)
    hit = next((int(r[0].split('=')[1]) for r in rows if r[1] == 'P'), None)
    rec = {'chunk': chunk, 'classified': [int(r[0].split('=')[1]) for r in rows], 'P': hit,
           'returncode': rc, 'stderr_tail': tail, 'seconds': round(time.monotonic() - start, 1)}
    with log.open('a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(time.strftime('%H:%M:%S'), f'batch {chunk[0]}..{chunk[-1]}: classified {len(rows)}/{len(chunk)}, P={hit}, '
          f'{rec["seconds"]}s', flush=True)
    if hit:
        print('WITNESS', hit, 'classified', n, 'skipped', skipped, flush=True)
        break
    if stopping:
        print('STOPPED by a signal after', n, 'classified; skipped', skipped, flush=True)
        sys.exit(124)
    if len(rows) < len(chunk):
        skipped.append(chunk[len(rows)])
        queue = chunk[len(rows) + 1:] + queue
        if len(skipped) >= a.max_skips:
            print('GAVE UP after', n, 'classified; skipped', skipped, flush=True)
            break
else:
    print('NO WITNESS up to', a.wmax, 'classified', n, 'skipped', skipped, flush=True)
