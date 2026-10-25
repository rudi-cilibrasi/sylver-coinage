"""For every legal even answer a to the reply 40 up to AMAX: a move from {16,40,a} into a known P-position."""
import sys
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position
from sylver.short_certificates import NODES
from screen import KNOWN
CERT = {key(n.generators): f'node {n.name}' for n in NODES}
CERT.update({key((16, 28, 38, 40)): 'B28 (r38 audit)', key((16, 30, 40, 44)): "Z' (Z audit)", key((16, 20, 46)): 'Q (here)',
             key((16, 36, 40, 58)): 'B58 (here)', key((2, 3)): 'finite {2,3}'})
SEARCH = {key((16, 40, 52, 54)): 'B54 (search)'}
amax = int(sys.argv[1])
for a in range(2, amax + 1, 2):
    if not legal((16, 40), a):
        continue
    base = position((16, 40, a))
    hit = next(((w, CERT[key(position((*base, w)))]) for w in range(2, 400) if legal(base, w)
                and key(position((*base, w))) in CERT), None)
    grade = 'certified'
    if not hit:
        hit = next(((w, (SEARCH | KNOWN)[key(position((*base, w)))]) for w in range(2, 400) if legal(base, w)
                    and key(position((*base, w))) in (SEARCH | KNOWN)), None)
        grade = 'search/known'
    print(a, a % 8, base, (grade, hit) if hit else '-')
