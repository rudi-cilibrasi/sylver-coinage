"""Find an even move e' of a gcd-two position C (short or long) with C+e' P; stop at the first.

For each even obligation e' of C: D = C+e'. If D is a known P-position, done.
If D is short: its odd obligations must all be N (finite sweeps), and then
each even obligation f of D must lead to N: a reply reaching a known P, or a
finite odd witness (for a long D+f, odd replies up to --wmax; for a short D+f
only its odd obligations count). Prints, for each D, how many of its
obligations were refuted; a D with all refuted is a P candidate (D P makes e'
win from C, so C is N).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from even_resolver import KNOWN, odd_witness  # noqa: E402
from sylver.arena.common import key, legal, position, profile  # noqa: E402


def short_info(p):
    info = profile(p)
    return info if info['complete'] and info['tail'] == 'quiet-end-v1' else None


def refute(child, args):
    """A winning reply from ``child`` (a known P or a finite odd witness), or None, with a note."""
    if key(child) in KNOWN:
        return None, 'is a known P-position'
    hit = next((w for w in range(2, 600) if legal(child, w) and key(position((*child, w))) in KNOWN), None)
    if hit:
        return hit, f'known P via {hit}'
    info = short_info(child)
    only = [m for m in info['moves'] if m % 2] if info else None
    w, tried, _ = odd_witness(child, args.wmax, args.batch, args.threads, args.max_states, args.timeout, only)
    if w:
        return w, f'odd witness {w}'
    return None, ('short, odd-complete' if info and tried == len(only) else f'open after {tried} odd')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('generators', nargs='+', type=int)
    ap.add_argument('--wmax', type=int, default=401)
    ap.add_argument('--batch', type=int, default=60)
    ap.add_argument('--threads', type=int, default=6)
    ap.add_argument('--max-states', type=int, default=400_000_000)
    ap.add_argument('--timeout', type=int, default=1800)
    args = ap.parse_args()
    c = position(tuple(args.generators))
    evens = profile(c)['even_moves']
    def size(e):
        i = profile(position((*c, e)))
        return i.get('half_frobenius') or 0
    evens = sorted(evens, key=lambda e: (size(e), e))
    print('C =', c, 'even moves:', evens, flush=True)
    for e in evens:
        d = position((*c, e))
        if key(d) in KNOWN:
            print(f"e'={e}: D={d} KNOWN P ({KNOWN[key(d)]}) -> C is N", flush=True)
            return
        dinfo = short_info(d)
        if not dinfo:
            print(f"e'={e}: D={d} long; skipped", flush=True)
            continue
        dodd = [m for m in dinfo['moves'] if m % 2]
        w, tried, _ = odd_witness(d, args.wmax, args.batch, args.threads, args.max_states, args.timeout, dodd)
        if w:
            print(f"e'={e}: D={d} N (odd obligation {w} wins)", flush=True)
            continue
        if tried < len(dodd):
            print(f"e'={e}: D={d} odd obligations incomplete ({tried}/{len(dodd)})", flush=True)
            continue
        devens = [m for m in dinfo['moves'] if m % 2 == 0]
        notes, open_ = {}, []
        for f in devens:
            reply, note = refute(position((*d, f)), args)
            notes[f] = note
            if reply is None:
                open_.append(f)
        verdict = 'P CANDIDATE' if not open_ else f'{len(open_)} open'
        print(f"e'={e}: D={d} odd-complete ({len(dodd)}); even {len(devens) - len(open_)}/{len(devens)} refuted; "
              f"{verdict}; open: {[(f, notes[f]) for f in open_]}", flush=True)
        if not open_:
            return


if __name__ == '__main__':
    main()
