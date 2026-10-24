#!/bin/bash
# Even obligations of 54, then 58, short children first (kunz_pt, 100M P-positions, 5 minutes a batch).
for r in 54 58; do
  echo "$(date '+%F %T') even short-first $r start" >> even_triage.log
  nice -n 10 /usr/bin/python3 even_resolver.py $r --short-first --p-table --ncache-mb 8192 --threads 10 \
      --max-states 100000000 --timeout 300 >> even_triage.log 2>&1
  rc=$?
  echo "$(date '+%F %T') even short-first $r end (exit $rc)" >> even_triage.log
done
