"""Re-check, without a solver, the unresolved obligations of the tested children against the
larger known list (screen.KNOWN, which grew as positions were found: 505 entries for
recheck_known.txt, 508 for recheck_known2.txt)."""
import json, sys
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position
from screen import KNOWN
for f in sys.argv[1:]:
    rows = {}
    for line in open(f):
        x = json.loads(line); rows[x['e']] = x
    left = {e: x for e, x in rows.items() if x['status'] != 'resolved'}
    print(f, len(rows), 'rows,', len(left), 'unresolved:', {e: x['status'] for e, x in sorted(left.items())})
    for e, x in sorted(left.items()):
        child = position(tuple(map(int, x['child'].split(','))))
        if key(child) in KNOWN:
            print('   ', e, 'its child is known P:', KNOWN[key(child)], '-> the tested position is N')
            continue
        hit = next(((w, KNOWN[key(position((*child, w)))]) for w in range(2, 600)
                    if legal(child, w) and key(position((*child, w))) in KNOWN), None)
        print('   ', e, 'known reply:', hit)
