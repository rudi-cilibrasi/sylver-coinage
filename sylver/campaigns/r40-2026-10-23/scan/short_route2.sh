#!/bin/bash
# As short_route.sh, but a short child whose odd obligations are all N is tested for P as soon as the
# short-only pass finds it (even_resolver.py --stop-at-needs-even), before the pass goes on: a P child
# refutes the candidate, and the rest of its pass is then not needed.
for r in "$@"; do
  prev=-1
  while :; do
    state=$(/usr/bin/python3 route_state.py $r) || { echo "$(date '+%F %T') route_state.py $r failed" >> even_triage.log; break; }
    eval "$state"
    if [ "$found" = True ] || [ "$refuted" = True ]; then break; fi
    if [ -n "$kids" ]; then ./test_children.sh $r $kids; continue; fi
    if [ "$left" = 0 ] || [ "$left" = "$prev" ]; then break; fi
    prev=$left
    echo "$(date '+%F %T') even short-only $r start (stopping at the next child that needs even replies)" >> even_triage.log
    nice -n 10 /usr/bin/python3 even_resolver.py $r --short-only --stop-at-needs-even --p-table --ncache-mb 8192 \
        --threads 10 --max-states 100000000 --timeout 300 >> even_triage.log 2>&1
    rc=$?
    echo "$(date '+%F %T') even short-only $r end (exit $rc)" >> even_triage.log
  done
done
