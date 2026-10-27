"""For each open row of resolve_<G>.jsonl, the odd replies for a deeper kunz_pt run: its skipped moves (each hit the
batch timeout, the likeliest P replies), then the moves the resolver never reached because it gave up after four
skips (odd w <= 401 after the last skipped one, in its Frobenius order). Prints 'e w,w,...' per open row.

Usage: pass_f_lists.py G...
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(HERE))
from sylver.arena.common import key, legal, position  # noqa: E402
from even_resolver import frobenius_number  # noqa: E402

base = position(tuple(map(int, sys.argv[1:])))
rows = {}
for line in (HERE / f"resolve_{key(base).replace(',', '-')}.jsonl").read_text().splitlines():
    row = json.loads(line)
    rows[row['e']] = row
for e, row in sorted(rows.items()):
    if row['status'] != 'open':
        continue
    child = position((*base, e))
    odd = [w for w in range(3, 402, 2) if legal(child, w)]
    odd.sort(key=lambda w: (frobenius_number(position((*child, w))), w))
    skipped = row['skipped']
    rest = odd[odd.index(skipped[-1]) + 1:] if skipped else []
    print(e, ','.join(map(str, skipped + rest)))
