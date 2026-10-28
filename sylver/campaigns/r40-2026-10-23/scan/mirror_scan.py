"""Answers to 40 refuted by a P-position the search found for another answer.

A P-position {16,40,x,y} found while refuting x (or in any sweep) also refutes the answer y when x is a legal move
from {16,40,y}. This collects the P-positions the scan's files record: the P rows of kunz_pt outputs (base + w is
P), their N rows (base + w + winning move is P), and the resolved rows of the resolver files (child + reply is P).
It prints each answer a, its move b and the position {16,40,a}+b, with the first file and line that gives it, for
every such position of the form {16,40,x,y}. All of it is search grade, as the files are. Outputs with no base (no
kunz_pt command line in their .err and none in BASES: replays and sweeps of positions with more generators) are
skipped, and the last line names them.

Usage: mirror_scan.py (no solver; it reads the files beside it).
"""
import glob, json, re, sys
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position  # noqa: E402

HERE = Path(__file__).resolve().parent
# outputs whose .err has no kunz_pt command line: their bases, from README.md
BASES = {'odd_answers.out': (16, 40), 'odd_answers2.out': (16, 40), 'odd_16-40-30.out': (16, 30, 40),
         'odd_16-40-38.out': (16, 38, 40)}


def base_of(out):
    if out.name in BASES:
        return BASES[out.name]
    err = out.with_suffix('.err')
    base = None
    if err.exists():
        for line in err.read_text(errors='replace').splitlines():
            m = re.search(r'--odd-list \S+ ((?:\d+ ?)+?)(?:;|\)|$)', line.strip())
            if m:
                base = tuple(int(x) for x in m.group(1).split())
    return base


found = {}   # position key -> first source
skipped = []
for out in sorted(HERE.glob('*.out')):
    base = base_of(out)
    if base is None:
        skipped.append(out.name)
        continue
    for i, line in enumerate(out.read_text(errors='replace').splitlines(), 1):
        if not line.startswith('move='):
            continue
        f = line.split()
        w = int(f[0].split('=')[1])
        pos = (*base, w) if f[1] == 'P' else (*base, w, int(f[2].split('=')[1]))
        found.setdefault(key(position(pos)), f'{out.name}:{i}')
for jf in sorted(HERE.glob('*.jsonl')):
    for i, line in enumerate(jf.read_text().splitlines(), 1):
        r = json.loads(line)
        if r.get('status') == 'resolved' and r.get('child') and r.get('reply'):
            found.setdefault(key(position((*map(int, r['child'].split(',')), r['reply']))), f'{jf.name}:{i}')

rows = set()
for k, src in found.items():
    g = [int(x) for x in k.split(',')]
    if len(g) != 4 or 16 not in g or 40 not in g:
        continue
    u, v = [x for x in g if x not in (16, 40)]
    for a, b in ((u, v), (v, u)):
        child = position((16, 40, a))
        if legal(position((16, 40)), a) and legal(child, b) and key(position((*child, b))) == k:
            rows.add((a, b, k, src))
for a, b, k, src in sorted(rows):
    print(f'{a} fails by {b}: {{{k}}} [{src}]')
print('skipped (no base):', ' '.join(skipped))
