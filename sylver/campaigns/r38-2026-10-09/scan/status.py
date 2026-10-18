"""Status of {16,38}'s obligations from the search logs (a move is an answer to 38 iff {16,38,move} is P)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from sylver.arena.common import legal, position, profile, key  # noqa: E402

HERE = Path(__file__).resolve().parent
info = profile(position((16, 38)))
status = {}
# odd: the o16 scan's first 24 (by Frobenius) are N; the shared sweep, then the per-candidate queue and retries, report the rest
odd = [m for m in info['moves'] if m % 2]
for name in ('odd_open.out', 'odd_queue.out', 'odd_retry.out'):   # the shared sweep, then each open candidate alone
    if not (HERE / name).exists():
        continue
    for line in (HERE / name).read_text().splitlines():
        m = re.match(r'move=(\d+) (\w) winning_move=(\S+)', line)
        if m:
            status[int(m[1])] = ('N' if m[2] == 'N' else 'P!', f'reply {m[3]}')
open_odd = {71, 69, 77, 79, 85, 93, 101, 87, 109, 117, 125}
for m in odd:
    if m not in open_odd:
        status[m] = ('N', 'o16 scan')
# short even candidates: odd filter, then resolvers / known refutations
for line in (HERE / 'odd_filter.jsonl').read_text().splitlines():
    row = json.loads(line)
    if row['P_moves']:
        status[row['r']] = ('N', f"odd {row['P_moves'][0]}")
known = json.loads((HERE / 'known_p.json').read_text())
for e in [m for m in info['moves'] if m % 2 == 0]:
    if e in status:
        continue
    base = position((16, 38, e))
    hit = next((f for f in range(2, 400, 2) if key(position((*base, f))) in known and f not in base), None)
    if hit:
        status[e] = ('N', f'even {hit} -> {known[key(position((*base, hit)))]}')
for line in (HERE / 'resolve_16-38-long.log').read_text().splitlines():
    m = re.match(r'r=16-38 e=\s*(\d+) (\S+)\s+reply=(\S+)', line)
    if m:
        status.setdefault(int(m[1]), ('N' if m[2] == 'resolved' else m[2], f'reply {m[3]}'))
# deeper sweeps of long candidates the map searched shallowly (deep_long.sh): a batch with a P reply is a witness
for path in sorted(HERE.glob('deep_16-38-*.jsonl')):
    rest = path.stem.split('-')[2:]
    if len(rest) != 1:          # files for the children of other candidates, such as 72's
        continue
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get('P'):
            status[int(rest[0])] = ('N', f"reply {row['P']} (deeper sweep)")
# 72: {16,38,72} is P by search when each of its obligations is N. Its odd ones: a row of the sweep
# over all of them (odd72_all.out) or of the earlier one over the last three (odd72.out), each naming
# a winning move. Its even ones: the even resolver (even_72.jsonl), B56 for 56 (the audit), a deeper
# sweep (deep_16-38-<e>-72 or deep_16-38-72-<e>) or a hunt witness (hunt.jsonl). The rungs 88, 104
# and 120 then move by 72 back to {16,38,72}: 88, 104 and 120 are 72 plus multiples of 16.
p72 = profile(position((16, 38, 72)))
odd_n = set()
for name in ('odd72.out', 'odd72_all.out'):
    for line in (HERE / name).read_text().splitlines():
        m = re.match(r'move=(\d+) N winning_move=(\d+) ', line)
        if m:
            assert legal(position((16, 38, 72, int(m[1]))), int(m[2])), line
            odd_n.add(int(m[1]))
even_n = {r['e'] for r in map(json.loads, (HERE / 'even_72.jsonl').read_text().splitlines()) if r['status'] == 'resolved'}
if '56' in json.loads((HERE.parent / 'audit.json').read_text())['refuted_answers_to_38']:
    even_n.add(56)
for path in HERE.glob('deep_16-38-*.jsonl'):
    rest = [int(x) for x in path.stem.split('-')[2:]]
    if len(rest) == 2 and 72 in rest and any(json.loads(l).get('P') for l in path.read_text().splitlines()):
        even_n.add(next(x for x in rest if x != 72))
for r in map(json.loads, (HERE / 'hunt.jsonl').read_text().splitlines()):
    if r['outcome'] == 'P':
        assert len(r['child']) == 4 and 72 in r['child'], r
        even_n.add(next(x for x in r['child'] if x not in (16, 38, 72)))
open72 = [m for m in p72['moves'] if m not in (odd_n if m % 2 else even_n)]
if not open72:
    assert status.get(72, ('?',))[0] != 'N', status[72]
    status[72] = ('P', 'every obligation of {16,38,72} is N: 72 answers 38')
    for rung in (88, 104, 120):
        status[rung] = ('N', 'even 72 -> {16,38,72}')
rows = []
for mv in info['moves']:
    st = status.get(mv, ('?', ''))
    ci = profile(position((16, 38, mv)))
    kind = 'odd' if mv % 2 else ('short' if ci['complete'] and ci['tail'] == 'quiet-end-v1' else 'long')
    rows.append((mv, kind, *st))
todo = [r for r in rows if r[2] != 'N']
answers = [r[0] for r in rows if r[2] == 'P']
print(f"{len(rows)} obligations; N: {sum(r[2] == 'N' for r in rows)}; P (answers to 38): {answers}; "
      f"open: {len(todo) - len(answers)}")
for r in todo:
    print(*r)
