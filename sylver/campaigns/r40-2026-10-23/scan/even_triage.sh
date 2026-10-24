#!/bin/bash
# First pass over the even obligations of the odd-complete candidates, cheapest settings:
# kunz_pt --p-table, 10 threads, 100M P-positions, 5 minutes a batch, lowest candidate first.
for r in 46 54 58; do
  echo "$(date '+%F %T') even triage $r start" >> even_triage.log
  nice -n 10 /usr/bin/python3 even_resolver.py $r --p-table --ncache-mb 8192 --threads 10 \
      --max-states 100000000 --timeout 300 >> even_triage.log 2>&1
  echo "$(date '+%F %T') even triage $r end (exit $?)" >> even_triage.log
done
