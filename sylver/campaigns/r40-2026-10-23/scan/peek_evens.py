"""List a gcd-two position's even moves e' with: D = C+e' short or long, whether D+44 is X, D's obligation counts."""
import sys
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import key, legal, position, profile
X = position((16, 40, 44, 66))
c = position(tuple(map(int, sys.argv[1:])))
info = profile(c)
print('C =', c, 'short' if info['complete'] and info['tail'] == 'quiet-end-v1' else 'long', 'even moves:', info['even_moves'])
for e in info['even_moves']:
    d = position((*c, e))
    di = profile(d)
    short = di['complete'] and di['tail'] == 'quiet-end-v1'
    x = legal(d, 44) and position((*d, 44)) == X
    if short:
        mv = di['moves']
        print(f"  e'={e}: D={d} SHORT odd {sum(m % 2 for m in mv)} even {sum(m % 2 == 0 for m in mv)}{' D+44=X' if x else ''}")
    else:
        print(f"  e'={e}: D={d} long{' D+44=X' if x else ''}")
