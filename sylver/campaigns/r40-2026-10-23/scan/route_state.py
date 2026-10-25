"""Where the short-child route stands for a candidate R, as shell assignments: kids, the short
children whose odd obligations are all N and not yet tested; left, the short even obligations without a
row; refuted, whether a row's child is a known P-position; found, whether a tested child was P."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import position, profile

r = int(sys.argv[1])
base = position((16, 40, r))
short = [m for m in profile(base)['moves'] if m % 2 == 0
         and (lambda i: i['complete'] and i['tail'] == 'quiet-end-v1')(profile(position((*base, m))))]
f = Path(f'even_{r}.jsonl')
rows = {x['e']: x for x in map(json.loads, f.read_text().splitlines())} if f.exists() else {}
log = Path('test_children.log').read_text() if Path('test_children.log').exists() else ''
tested = {int(e) for e in re.findall(rf'test child \{{16,40,{r}\}}\+(\d+) end', log)}
kids = [e for e, x in sorted(rows.items()) if x['status'] == 'short: needs even' and e not in tested]
print(f"kids='{' '.join(map(str, kids))}'")
print(f'left={sum(1 for e in short if e not in rows)}')
print(f"refuted={any(x['status'] == 'REFUTES r' for x in rows.values())}")
print(f"found={bool(re.search(rf'\{{16,40,{r}\}}\+\d+ is P', log))}")
