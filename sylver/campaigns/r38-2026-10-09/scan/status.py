"""Status of {16,38}'s obligations from the search logs (a move is an answer to 38 iff {16,38,move} is P)."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import position, profile, key

HERE = Path(__file__).resolve().parent
info = profile(position((16, 38)))
status = {}
# odd: the o16 scan's first 24 (by Frobenius) are N; the open sweep reports the rest
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
rows = []
for mv in info['moves']:
    st = status.get(mv, ('?', ''))
    ci = profile(position((16, 38, mv)))
    kind = 'odd' if mv % 2 else ('short' if ci['complete'] and ci['tail'] == 'quiet-end-v1' else 'long')
    rows.append((mv, kind, *st))
todo = [r for r in rows if r[2] != 'N']
print(f"{len(rows)} obligations; N: {sum(r[2] == 'N' for r in rows)}; not yet N: {len(todo)}")
for r in todo:
    print(*r)
