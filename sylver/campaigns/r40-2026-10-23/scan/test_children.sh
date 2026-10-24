#!/bin/bash
# Is a short child of a candidate, whose odd obligations are all N, itself P? Resolve its even
# obligations (short children first); a child with every obligation resolved is P and refutes the candidate.
# Usage: test_children.sh R E... (children {16,40,R,E})
r=$1; shift
for e in "$@"; do
  echo "$(date '+%F %T') test child {16,40,$r}+$e start" >> test_children.log
  nice -n 10 /usr/bin/python3 even_resolver.py --position 16 40 $r $e --short-first --p-table --ncache-mb 8192 \
      --threads 10 --max-states 100000000 --timeout 300 >> test_children.log 2>&1
  rc=$?
  echo "$(date '+%F %T') test child {16,40,$r}+$e end (exit $rc)" >> test_children.log
  # every even obligation resolved: the child is P, so the candidate is refuted; the rest are not needed
  if tail -n 2 test_children.log | /usr/bin/python3 -c "
import re, sys
m = re.search(r\"summary: \{'resolved': (\d+), 'short: needs even': 0, 'open': 0, 'REFUTES r': 0\} of (\d+)\", sys.stdin.read())
sys.exit(0 if m and m[1] == m[2] else 1)"; then
    echo "$(date '+%F %T') {16,40,$r}+$e is P: $r is refuted; stopping" >> test_children.log
    break
  fi
done
