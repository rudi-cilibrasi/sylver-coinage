"""Resolve the even obligations of an arbitrary short position (generators on the command line).

--only-long skips the obligations whose child is short (handled by odd_filter.py and pair_search.py).

Each even obligation e reaches the gcd-two position C = P+e, which must be
N for the given short position P to be P. For each e: (1) a reply w that reaches a
known P-position (known_p.json: certified nodes, published positions, Book P
targets, W, U); else (2) the least odd w whose finite C+w is P, by kunz_solver
sweeps in one shared memo per batch, in increasing Frobenius order, up to
--wmax. Writes even_<r>.jsonl (one row per obligation) and prints a summary.
An obligation whose child C is itself a known P-position refutes r.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
ENGINE = HERE / 'kunz'
KNOWN = json.loads((HERE / 'known_p.json').read_text())
REPLY = 38


SKIPPED = []     # odd replies whose sweep hit the memory or time limit (unclassified)
MAX_SKIPS = 4


def odd_witness(child, wmax, batch, threads, max_states, timeout, only=None):
    """Least odd w <= wmax (or in ``only``) with child+w P (sweeps in batches), or None; with rows tried."""
    odd = sorted(only) if only is not None else [w for w in range(3, wmax + 1, 2) if legal(child, w)]
    odd.sort(key=lambda w: (frobenius_number(position((*child, w))), w))
    tried, queue = 0, list(odd)
    SKIPPED.clear()
    while queue:
        chunk, queue = queue[:batch], queue[batch:]
        argv = [str(ENGINE), '--threads', str(threads), '--stop-at-p', '--max-states', str(max_states),
                '--odd-list', ','.join(map(str, chunk)), *map(str, child)]
        try:
            out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout).stdout
        except subprocess.TimeoutExpired as error:
            out = (error.stdout or b'').decode()
        rows = [line.split() for line in out.splitlines() if line.startswith('move=')]
        tried += len(rows)
        for row in rows:
            if row[1] == 'P':
                return int(row[0].split('=')[1]), tried, int(row[4].split('=')[1])
        if len(rows) < len(chunk):   # stopped early (memory or time): skip the move in progress, go on
            SKIPPED.append(chunk[len(rows)])
            queue = chunk[len(rows) + 1:] + queue
            if len(SKIPPED) >= MAX_SKIPS:
                return None, tried, None
    return None, tried, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('generators', nargs='+', type=int)
    ap.add_argument('--wmax', type=int, default=401)
    ap.add_argument('--batch', type=int, default=60)
    ap.add_argument('--threads', type=int, default=10)
    ap.add_argument('--max-states', type=int, default=700_000_000)
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('--only-long', action='store_true')
    args = ap.parse_args()
    base = position(tuple(args.generators))
    args.r = '-'.join(map(str, base))
    info = profile(base)
    assert info['complete'] and info['tail'] == 'quiet-end-v1', 'not short'
    even = [m for m in info['moves'] if m % 2 == 0]
    out = HERE / f'resolve_{args.r}.jsonl'
    done = {json.loads(l)['e'] for l in out.read_text().splitlines()} if out.exists() else set()
    for e in even:
        if e in done:
            continue
        child = position((*base, e))
        if args.only_long:
            ci = profile(child)
            if ci['complete'] and ci['tail'] == 'quiet-end-v1':
                continue
        start = time.monotonic()
        row = {'e': e, 'child': key(child)}
        if key(child) in KNOWN:
            row.update(status='REFUTES r', via=KNOWN[key(child)])
        else:
            hit = next(((w, KNOWN[key(position((*child, w)))]) for w in range(2, 600)
                        if legal(child, w) and key(position((*child, w))) in KNOWN), None)
            if hit:
                row.update(status='resolved', reply=hit[0], via=hit[1])
            else:
                # A short child is N only through one of its obligations (Quiet End
                # Theorem): its odd candidates are its odd obligations, all below its
                # half's Frobenius number; a long child has no such bound.
                cinfo = profile(child)
                short = cinfo['complete'] and cinfo['tail'] == 'quiet-end-v1'
                only = [m for m in cinfo['moves'] if m % 2] if short else None
                w, tried, states = odd_witness(child, args.wmax, args.batch, args.threads, args.max_states,
                                               args.timeout, only)
                status = 'resolved' if w else ('short: needs even' if short and tried == len(only) else 'open')
                row.update(status=status, reply=w, via='finite odd witness' if w else None, odd_tried=tried,
                           skipped=list(SKIPPED),
                           states=states, child_short=short,
                           child_even_obligations=[m for m in cinfo['moves'] if m % 2 == 0] if short else None)
        row['seconds'] = round(time.monotonic() - start, 1)
        with out.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        print(f"r={args.r} e={e:4} {row['status']:9} reply={row.get('reply')} via={row.get('via')} "
              f"tried={row.get('odd_tried', '-')} {row['seconds']}s", flush=True)
        if row['status'] == 'REFUTES r':
            break
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    print('summary:', {s: sum(1 for x in rows if x['status'] == s) for s in ('resolved', 'short: needs even', 'open', 'REFUTES r')},
          'of', len(even), flush=True)


if __name__ == '__main__':
    main()
