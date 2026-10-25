#!/bin/bash
# Finite odd replies for B78's moves 20, 34 and 46, in place of the resolver's routes (20 and 46 reach Q; 34 reaches
# {8,34,36}, on Sicherman's list): odd w up to 201 in the resolver's order, as q_finite.sh did for Q.
order() { /usr/bin/python3 -c "
import sys; sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position
from sylver.solver import frobenius_number
c = position(tuple(map(int, sys.argv[1:])))
odd = sorted((w for w in range(3, 202, 2) if legal(c, w)), key=lambda w: (frobenius_number(position((*c, w))), w))
print(','.join(map(str, odd)))" "$@"; }
for e in 20 34 46; do
  echo "$(date '+%F %T') start" > b78_finite_$e.err
  nice ./kunz --threads 2 --stop-at-p --max-states 100000000 --odd-list "$(order 16 36 40 78 $e)" 16 36 40 78 $e > b78_finite_$e.out 2>> b78_finite_$e.err
  rc=$?
  echo "$(date '+%F %T') exit $rc" >> b78_finite_$e.err
  echo "$e: $(tail -n 1 b78_finite_$e.out)"
done
