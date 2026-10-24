#!/bin/bash
# Finite odd replies for Q's moves 8, 24, 26 and 30, in place of routes through G, K and O
# (which rest on {8,10,22} or Blok's pairing family): odd w up to 201 in the resolver's order.
order() { /usr/bin/python3 -c "
import sys; sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import legal, position
from sylver.solver import frobenius_number
c = position(tuple(map(int, sys.argv[1:])))
odd = sorted((w for w in range(3, 202, 2) if legal(c, w)), key=lambda w: (frobenius_number(position((*c, w))), w))
print(','.join(map(str, odd)))" "$@"; }
for e in 8 24 26 30; do
  nice ./kunz --threads 2 --stop-at-p --max-states 100000000 --odd-list "$(order 16 20 46 $e)" 16 20 46 $e > q_finite_$e.out 2> q_finite_$e.err
  echo "$e: $(tail -n 1 q_finite_$e.out)"
done
