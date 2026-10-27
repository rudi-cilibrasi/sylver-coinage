"""Odd replies w <= WMAX to a gcd-two position C, in the resolver's order (Frobenius number of C+w, then w),
after the reply AFTER (exclusive): the candidates for another, cheaper finite witness. Prints them comma-separated.

Usage: alt_list.py AFTER WMAX C...
"""
import sys
from pathlib import Path
sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sylver.arena.common import legal, position  # noqa: E402
from even_resolver import frobenius_number  # noqa: E402

after, wmax = int(sys.argv[1]), int(sys.argv[2])
c = position(tuple(map(int, sys.argv[3:])))
odd = sorted((w for w in range(3, wmax + 1, 2) if legal(c, w)), key=lambda w: (frobenius_number(position((*c, w))), w))
print(','.join(map(str, odd[odd.index(after) + 1:])))
