"""Even rows of {16,40,a} that its odd rows settle, appended to even_<a>.jsonl before even_resolver.py runs.

An odd row 'move=w N winning_move=e' of {16,40,a} (kunz_pt --odd-list, deep_<a>*.out) says {16,40,a,w,e} is P.
When e is an even obligation of {16,40,a}, that position is also its child {16,40,a,e} plus the odd reply w,
so the child is N by w and the obligation e is met (search grade, as the odd row is). The rows say which file
and row they came from. A deep_<a>*.out file is read only when the last kunz_pt command line in its .err has
the base {16,40,a} (deep_86+105.out does; deep_82+60+84.out, a sweep of {16,40,60,82,84}, does not).
With --b66, also 82's obligations 44 and 66, which B66={16,40,44,66} (P by search,
evidence_16-40-44-66.json) meets: {16,40,44,82}+66 and {16,40,66}+44 are B66 (82 = 16+66).
With --known, also each obligation whose child reaches a known P-position (screen.py's KNOWN) by a reply below
600: the reply lookup even_resolver.py makes first, here for rows it would not redo (such as 'short: needs
even'). A child that is itself in KNOWN (which refutes a) gets no row here; even_resolver.py reports it.
KNOWN does not hold this record's finite witnesses (such as {11,16,26,40}).
Usage: cross_rows.py a [--b66] [--known]. A row is added only for an obligation whose latest row is not 'resolved'.
Not while even_resolver.py runs on the same a: it reads its file once, at its start, and a row it writes later
for the same obligation would become the latest.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile  # noqa: E402

HERE = Path(__file__).resolve().parent
a = int(sys.argv[1])
base = position((16, 40, a))
even = {m for m in profile(base)['moves'] if m % 2 == 0}
out = HERE / f'even_{a}.jsonl'
latest = {x['e']: x for x in map(json.loads, out.read_text().splitlines())}


def base_of(f):
    """The position of the last kunz_pt --odd-list command line in f's .err, or None."""
    err, found = f.with_suffix('.err'), None
    if err.exists():
        for line in err.read_text(errors='replace').splitlines():
            m = re.search(r'--odd-list \S+ ((?:\d+ ?)+?)(?:;|\)|$)', line.strip())
            if m:
                found = position(tuple(int(x) for x in m.group(1).split()))
    return found


new = {}
for f in sorted(HERE.glob(f'deep_{a}*.out')):
    if base_of(f) != base:
        continue
    for line in f.read_text().splitlines():
        if not line.startswith('move='):
            continue
        if line.split()[1] != 'N':   # a P row has winning_move=none
            continue
        fields = dict(part.split('=') for part in line.split()[2:])
        w, e = int(line.split()[0].split('=')[1]), int(fields['winning_move'])
        if e not in even or e in new:
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
if '--known' in sys.argv[2:]:
    sys.path.insert(0, str(HERE))
    from screen import KNOWN  # noqa: E402
    for e in sorted(even - set(new)):
        if latest.get(e, {}).get('status') == 'resolved':
            continue
        child = position((*base, e))
        hit = next((w for w in range(2, 600) if legal(child, w) and key(position((*child, w))) in KNOWN), None)
        if hit:
            k = key(position((*child, hit)))
            new[e] = {'e': e, 'child': key(child), 'status': 'resolved', 'reply': hit,
                      'via': f'{{{key(child)}}}+{hit} is {{{k}}}, P: {KNOWN[k]}'}
with out.open('a') as fh:
    for e in sorted(new):
        if latest.get(e, {}).get('status') == 'resolved':
            continue
        row = {**new[e], 'seconds': 0.0}
        fh.write(json.dumps(row) + '\n')
        print(json.dumps(row))
