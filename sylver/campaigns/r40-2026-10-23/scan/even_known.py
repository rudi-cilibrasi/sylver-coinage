"""Stage 1 of even_resolver.py only (no solver): for each even obligation e of {16,40,r},
look for a reply w whose position reaches KNOWN; report the rest with their child's shape."""
import sys
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile
from screen import KNOWN

for r in map(int, sys.argv[1:]):
    base = position((16, 40, r))
    even = [m for m in profile(base)['moves'] if m % 2 == 0]
    res, rest = 0, []
    for e in even:
        child = position((*base, e))
        if key(child) in KNOWN:
            print(r, e, 'REFUTES', KNOWN[key(child)]); continue
        hit = next((w for w in range(2, 600) if legal(child, w) and key(position((*child, w))) in KNOWN), None)
        if hit:
            res += 1; continue
        ci = profile(child)
        short = ci['complete'] and ci['tail'] == 'quiet-end-v1'
        odd = [m for m in ci['moves'] if m % 2] if short else None
        rest.append((e, child, short, len(odd) if odd is not None else None))
    print(f'r={r}: {len(even)} even obligations, {res} by a known reply, {len(rest)} left')
    for e, child, short, nodd in rest:
        print(f'   e={e:4} child={child} short={short} odd_obligations={nodd}')
