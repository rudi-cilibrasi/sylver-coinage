#!/bin/bash
# Small odd sweeps kept for the record: Q's move 22 child, and the odd obligations of {16,40,30} and {16,40,38}.
odd() { /usr/bin/python3 -c "
import sys; sys.path.insert(0, '/home/ruclaw/src/sylver-coinage')
from sylver.arena.common import profile, position
print(','.join(str(m) for m in profile(position(tuple(map(int, sys.argv[1:]))))['moves'] if m % 2))" "$@"; }
nice ./kunz --threads 2 --stop-at-p --max-states 30000000 --odd-list "$(tail -1 w22.txt)" 16 20 22 46 > odd_16-20-22-46.out 2> odd_16-20-22-46.err
for a in 30 38; do
  nice ./kunz --threads 2 --stop-at-p --max-states 60000000 --odd-list "$(odd 16 40 $a)" 16 40 $a > odd_16-40-$a.out 2> odd_16-40-$a.err
done
