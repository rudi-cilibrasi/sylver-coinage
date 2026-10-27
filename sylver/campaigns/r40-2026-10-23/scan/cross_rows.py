"""Even rows of {16,40,a} that its odd rows settle, appended to even_<a>.jsonl before even_resolver.py runs.

An odd row 'move=w N winning_move=e' of {16,40,a} (kunz_pt --odd-list, deep_<a>*.out) says {16,40,a,w,e} is P.
When e is an even obligation of {16,40,a}, that position is also its child {16,40,a,e} plus the odd reply w,
so the child is N by w and the obligation e is met (search grade, as the odd row is). The rows say which file
and row they came from. With --b66, also 82's obligations 44 and 66, which B66={16,40,44,66} (P by search,
evidence_16-40-44-66.json) meets: {16,40,44,82}+66 and {16,40,66}+44 are B66 (82 = 16+66).
Usage: cross_rows.py a [--b66]. A row is added only for an obligation whose latest row is not 'resolved'.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402

HERE = Path(__file__).resolve().parent
a = int(sys.argv[1])
base = position((16, 40, a))
even = {m for m in profile(base)['moves'] if m % 2 == 0}
out = HERE / f'even_{a}.jsonl'
latest = {x['e']: x for x in map(json.loads, out.read_text().splitlines())}
new = {}
for f in sorted(HERE.glob(f'deep_{a}*.out')):
    if f.name[len(f'deep_{a}'):-len('.out')] not in ('', 'x'):
        continue
    for line in f.read_text().splitlines():
        if not line.startswith('move='):
            continue
        fields = dict(part.split('=') for part in line.split()[2:])
        w, e = int(line.split()[0].split('=')[1]), int(fields['winning_move'])
        if line.split()[1] != 'N' or e not in even or e in new:
            continue
        child = position((*base, e))
        assert legal(child, w) and legal(position((*base, w)), e)
        new[e] = {'e': e, 'child': key(child), 'status': 'resolved', 'reply': w,
                  'via': f'{f.name}: {{16,40,{a}}}+{w} N by {e} (search), so {{16,40,{a},{e}}}+{w} is P'}
if '--b66' in sys.argv[2:]:
    assert a == 82
    for e, w in ((44, 66), (66, 44)):
        child = position((*base, e))
        assert legal(child, w) and position((*child, w)) == (16, 40, 44, 66)
        new.setdefault(e, {'e': e, 'child': key(child), 'status': 'resolved', 'reply': w,
                           'via': 'B66 P by search (evidence_16-40-44-66.json)'})
with out.open('a') as fh:
    for e in sorted(new):
        if latest.get(e, {}).get('status') == 'resolved':
            continue
        row = {**new[e], 'seconds': 0.0}
        fh.write(json.dumps(row) + '\n')
        print(json.dumps(row))
