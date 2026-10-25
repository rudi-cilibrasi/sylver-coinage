#!/bin/bash
# B78's move 20 (B78+20 reduces to {16,20,78}): no odd reply up to 201 wins (b78_finite_20.out). Try the odd w from
# 203 to 601, in the resolver's order, with a 200M cap, before using the route through Q (the reply 46).
order() { /usr/bin/python3 -c "
import sys; sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position
from sylver.solver import frobenius_number
c = position(tuple(map(int, sys.argv[1:])))
odd = sorted((w for w in range(203, 602, 2) if legal(c, w)), key=lambda w: (frobenius_number(position((*c, w))), w))
print(','.join(map(str, odd)))" "$@"; }
echo "$(date '+%F %T') start" > b78_finite_20b.err
nice ./kunz --threads 2 --stop-at-p --max-states 200000000 --odd-list "$(order 16 36 40 78 20)" 16 36 40 78 20 > b78_finite_20b.out 2>> b78_finite_20b.err
rc=$?
echo "$(date '+%F %T') exit $rc" >> b78_finite_20b.err
echo "20 (203 to 601): $(tail -n 1 b78_finite_20b.out)"
