"""Child sweep of a finite position X = {16, 38, W}: the first move m with X+m P, which proves X N.

The children X+m are solved smallest Frobenius number first, each under a state cap. Odd children
are solved in batches sharing one memo (kunz --odd-list on the base X). An even child m is
{16, 38, m} + W, solved on the gcd-two base {16, 38, m}. The partner rule prunes and finds witnesses:
when X+m is N with winning move v, X+m+v is P, so if m is legal in X+v then X+v is N (winning move
m) and needs no solve, and if m is generated in X+v then X+v = X+m+v is P, a witness.

A P child m also settles {16, 38, m}: it is N by the reply W when W is legal there.
Appends one JSON line per run to child_<X>.jsonl, and on a SIGTERM records the rows of the run in
progress (returncode "timeout").

Usage: child_sweep.py W [--max-states S] [--threads T] [--batch B] [--max-skips K] [--even-first]
With --even-first, every even child comes before the odd ones (even children are cheap to solve);
--parity even (or odd) sweeps only those children.
"""
import argparse, json, signal, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('w', type=int)
ap.add_argument('--max-states', type=int, default=400_000_000)
ap.add_argument('--threads', type=int, default=2)
ap.add_argument('--batch', type=int, default=20)
ap.add_argument('--max-skips', type=int, default=40)
ap.add_argument('--even-first', action='store_true')
ap.add_argument('--parity', choices=('all', 'even', 'odd'), default='all')
a = ap.parse_args()
X = position((16, 38, a.w))
LOG = HERE / f"child_{key(X).replace(',', '-')}.jsonl"
moves = [m for m in range(2, frobenius_number(X) + 1) if legal(X, m)]
fro = {m: frobenius_number(position((*X, m))) for m in moves}
done = {}                                   # m -> ('N', v) | ('P', None) | ('skip', None)
if LOG.exists():                            # resume: keep what earlier runs classified
    for rec in map(json.loads, LOG.read_text().splitlines()):
        for m, outcome, v in rec['rows']:
            done[m] = (outcome, v)


class Stop(Exception):
    pass


stopping = reading = False


def on_term(signum, frame):
    global stopping
    stopping = True
    if reading:
        raise Stop


signal.signal(signal.SIGTERM, on_term)


def run(argv):
    """Run kunz, returning its move rows [(move, outcome, winning move or None)], the return code and the stderr tail."""
    global reading
    rows = []

    def take(line):
        if line.startswith('move='):
            f = line.split()
            v = f[2].split('=')[1]
            rows.append((int(f[0].split('=')[1]), f[1], None if v == 'none' else int(v)))

    with tempfile.TemporaryFile('w+') as err:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=err, text=True)
        reading = True
        try:
            for line in proc.stdout:
                take(line)
            rc = proc.wait()
        except Stop:
            rc = 'timeout'
        finally:
            reading = False
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        try:
            for line in proc.stdout:
                take(line)
        except (OSError, ValueError):
            pass
        err.seek(0)
        return rows, rc, err.read()[-300:]


def kunz(base, odd_moves):
    return [str(HERE / 'kunz'), '--threads', str(a.threads), '--stop-at-p', '--max-states', str(a.max_states),
            '--odd-list', ','.join(map(str, odd_moves)), *map(str, base)]


def record(rec):
    with LOG.open('a') as fh:
        fh.write(json.dumps(rec) + '\n')


def partner(m, v):
    """After X+m is N with winning move v: v's status, if the partner rule gives one."""
    if v is None or v not in fro or v in done:
        return None
    if legal(position((*X, v)), m):
        return ('N', m)                     # X+v+m = X+m+v is P
    return ('P', None)                      # X+v = X+m+v is P


wanted = {'all': (0, 1), 'even': (0,), 'odd': (1,)}[a.parity]
queue = sorted((m for m in moves if m not in done and m % 2 in wanted), key=lambda m: (a.even_first and m % 2, fro[m], m))
witness = next((m for m, (o, _) in done.items() if o == 'P'), None)
skips = sum(o == 'skip' for o, _ in done.values())
print(time.strftime('%H:%M:%S'), 'X =', X, 'F =', frobenius_number(X), 'moves', len(moves), 'left', len(queue),
      'witness', witness, flush=True)
while queue and witness is None and not stopping:
    m = queue.pop(0)
    if m in done:
        continue
    if m % 2:                               # a batch of the next odd moves in order
        chunk = [m] + [x for x in queue if x % 2 and x not in done][:a.batch - 1]
        argv, base = kunz(X, chunk), X
    else:
        chunk = [m]
        base = position((16, 38, m))
        argv = kunz(base, [a.w])
    start = time.monotonic()
    rows, rc, tail = run(argv)
    out = []
    for move, outcome, v in rows:
        child = move if m % 2 else m        # an even run's row is about the odd move W on the base {16,38,m}
        done[child] = (outcome, v)
        out.append([child, outcome, v])
        if outcome == 'P':
            witness = child
        else:
            got = partner(child, v)
            if got:
                done[v] = got
                out.append([v, got[0], got[1]])
                if got[0] == 'P':
                    witness = v
    finished = {c for c, _, _ in out}
    if rc != 'timeout' and not stopping and witness is None and len(rows) < len(chunk):
        skipped = chunk[len(rows)]          # the move in progress when the cap was reached
        done[skipped] = ('skip', None)
        out.append([skipped, 'skip', None])
        skips += 1
    record({'base': list(base), 'chunk': chunk, 'rows': out, 'returncode': rc, 'stderr_tail': tail,
            'seconds': round(time.monotonic() - start, 1)})
    queue = [x for x in queue if x not in done]
    print(time.strftime('%H:%M:%S'), f"m={m} chunk {len(chunk)}: classified {len(rows)}, "
          f"{sum(1 for c in finished if done[c][0] == 'N')} N, witness {witness}, {round(time.monotonic() - start)}s, "
          f"left {len(queue)}", flush=True)
    if skips >= a.max_skips:
        print('GAVE UP after', skips, 'skips', flush=True)
        break
if witness is not None:
    also = legal(position((16, 38, witness)), a.w)
    print('WITNESS', witness, 'X+m P' + (f'; {{16,38,{witness}}} is N by {a.w} too' if also else ''), flush=True)
elif stopping:
    print('STOPPED by a signal', flush=True)
    sys.exit(124)
else:
    print('NO WITNESS; left', len(queue), flush=True)
