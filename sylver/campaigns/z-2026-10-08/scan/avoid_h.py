"""Finite odd witnesses for obligations the resolver routed through K, O or S.

Those nodes reach Sicherman's {8,10,22} (published long position H). For each
listed (position, obligation), sweep odd replies w up to --wmax (or, for a
short child, its odd obligations) for a finite P destination, ignoring known
nodes, and report the least one with its standalone sequential state count.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from even_resolver import odd_witness  # noqa: E402
from sylver.arena.common import key, position, profile  # noqa: E402

CASES = {(16, 30, 40, 44): [10, 20, 24, 34], (16, 30, 56): [10, 20, 24]}


def main(wmax=601):
    out = {}
    for base, moves in CASES.items():
        for m in moves:
            child = position((*base, m))
            info = profile(child)
            short = info['complete'] and info['tail'] == 'quiet-end-v1'
            only = [x for x in info['moves'] if x % 2] if short else None
            w, tried, _ = odd_witness(child, wmax, 60, 8, 600_000_000, 3600, only)
            states = None
            if w:
                line = subprocess.run([str(HERE / 'kunz'), '--threads', '1', *map(str, position((*child, w)))],
                                      capture_output=True, text=True, check=True).stdout.split()
                states = int(line[3].split('=')[1])
            out[f"{'-'.join(map(str, base))}+{m}"] = {'child': key(child), 'short': short, 'witness': w,
                                                     'tried': tried, 'states': states}
            print(json.dumps({'base': base, 'm': m, **out[f"{'-'.join(map(str, base))}+{m}"]}), flush=True)
    (HERE / 'avoid_h.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
