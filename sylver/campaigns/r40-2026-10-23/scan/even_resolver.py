"""Resolve the even obligations of a short candidate answer {16,REPLY,r} (REPLY = 40 here).

A copy of the reply-38 campaign's scan/even_resolver.py with REPLY = 40, writing to this directory,
and KNOWN extended as screen.py extends it.

Each even obligation e reaches the gcd-two position C = {16,REPLY,r,e}, which
must be N for {16,REPLY,r} to be P. For each e: (1) a reply w that reaches a
known P-position (known_p.json: certified nodes, published positions, Book P
targets, W, U); else (2) the least odd w whose finite C+w is P, by kunz_solver
sweeps in one shared memo per batch, in increasing Frobenius order, up to
--wmax. Writes even_<r>.jsonl (one row per obligation) and prints a summary.
An obligation whose child C is itself a known P-position refutes r.
Before searching, a child is also looked up in the other candidates' even_*.jsonl rows
(the same child resolved there) and, for a child {16,40,c}, in screen.jsonl (the odd
move that refuted c); both are search-grade, and the row says which it used.
With --p-table the sweeps use kunz_pt --p-table (the cap then counts P-positions).
With --redo-open, obligations whose latest row is 'open' are tried again (the latest row per e counts).
With --short-first, the obligations whose child is short come first (their odd sweeps are bounded);
with --short-only, only those. With --stop-at-needs-even, it stops after the first new row whose child is
short with every odd obligation N (status 'short: needs even'), so that child can be tested for P first.
With --position G..., it resolves the even obligations of that short position instead, writing resolve_<G>.jsonl.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402
from sylver.solver import frobenius_number  # noqa: E402

HERE = Path(__file__).resolve().parent
ENGINE = HERE / 'kunz'
ENGINE_PT = HERE / 'kunz_pt'      # sylver/kunz_solver.cpp --p-table at e335ff0
ENGINE_ARGS = [str(ENGINE)]                       # main() sets [kunz] or [kunz_pt, --p-table, --ncache-mb, MB]
sys.path.insert(0, str(HERE))
from screen import KNOWN  # noqa: E402  (known_p.json plus the opening-16 finite P-positions)
REPLY = 40


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
        argv = [*ENGINE_ARGS, '--threads', str(threads), '--stop-at-p', '--max-states', str(max_states),
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
    ap.add_argument('r', type=int, nargs='?')
    ap.add_argument('--position', type=int, nargs='+')
    ap.add_argument('--wmax', type=int, default=401)
    ap.add_argument('--batch', type=int, default=60)
    ap.add_argument('--threads', type=int, default=10)
    ap.add_argument('--max-states', type=int, default=700_000_000)
    ap.add_argument('--timeout', type=int, default=1800)
    ap.add_argument('--p-table', action='store_true')
    ap.add_argument('--ncache-mb', type=int, default=8192)
    ap.add_argument('--redo-open', action='store_true')
    ap.add_argument('--short-first', action='store_true')
    ap.add_argument('--short-only', action='store_true')
    ap.add_argument('--stop-at-needs-even', action='store_true')
    args = ap.parse_args()
    ENGINE_ARGS[:] = ([str(ENGINE_PT), '--p-table', '--ncache-mb', str(args.ncache_mb)] if args.p_table
                      else [str(ENGINE)])
    elsewhere = {}                     # child key -> (reply, via) from other candidates' rows and the screen
    for f in sorted(HERE.glob('even_*.jsonl')):
        if f.name != f'even_{args.r}.jsonl' or args.position:
            for x in map(json.loads, f.read_text().splitlines()):
                if x['status'] == 'resolved':
                    elsewhere.setdefault(x['child'], (x['reply'], f'{f.name}: {x["via"]}'))
    if (HERE / 'screen.jsonl').exists():
        for x in map(json.loads, (HERE / 'screen.jsonl').read_text().splitlines()):
            if x['stage'] == 'odd' and x['refuted']:
                elsewhere.setdefault(key(position((16, REPLY, x['a']))), (x['by'], 'screen.jsonl: odd child P (search)'))
    base = position(tuple(args.position)) if args.position else position((16, REPLY, args.r))
    info = profile(base)
    assert info['complete'] and info['tail'] == 'quiet-end-v1', 'not short'
    even = [m for m in info['moves'] if m % 2 == 0]
    def is_short(e):
        i = profile(position((*base, e)))
        return i['complete'] and i['tail'] == 'quiet-end-v1'
    if args.short_only:
        even = [e for e in even if is_short(e)]
    elif args.short_first:
        even.sort(key=lambda e: (not is_short(e), e))
    out = HERE / (f"resolve_{key(base).replace(',', '-')}.jsonl" if args.position else f'even_{args.r}.jsonl')
    latest = {x['e']: x for x in map(json.loads, out.read_text().splitlines())} if out.exists() else {}
    done = {e for e, x in latest.items() if not (args.redo_open and x['status'] == 'open')}
    for e in even:
        if e in done:
            continue
        child = position((*base, e))
        start = time.monotonic()
        row = {'e': e, 'child': key(child)}
        if key(child) in KNOWN:
            row.update(status='REFUTES r', via=KNOWN[key(child)])
        else:
            hit = next(((w, KNOWN[key(position((*child, w)))]) for w in range(2, 600)
                        if legal(child, w) and key(position((*child, w))) in KNOWN), None)
            if hit:
                row.update(status='resolved', reply=hit[0], via=hit[1])
            elif key(child) in elsewhere:
                row.update(status='resolved', reply=elsewhere[key(child)][0], via=elsewhere[key(child)][1])
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
                           child_even_obligations=[m for m in cinfo['moves'] if m % 2 == 0] if short else None,
                           engine=Path(ENGINE_ARGS[0]).name, max_states=args.max_states, timeout=args.timeout)
        row['seconds'] = round(time.monotonic() - start, 1)
        with out.open('a') as fh:
            fh.write(json.dumps(row) + '\n')
        print(f"r={args.r} e={e:4} {row['status']:9} reply={row.get('reply')} via={row.get('via')} "
              f"tried={row.get('odd_tried', '-')} {row['seconds']}s", flush=True)
        if row['status'] == 'REFUTES r' or (args.stop_at_needs_even and row['status'] == 'short: needs even'):
            break
    rows = list({x['e']: x for x in map(json.loads, out.read_text().splitlines())}.values())
    print('summary:', {s: sum(1 for x in rows if x['status'] == s) for s in ('resolved', 'short: needs even', 'open', 'REFUTES r')},
          'of', len(even), flush=True)


if __name__ == '__main__':
    main()
