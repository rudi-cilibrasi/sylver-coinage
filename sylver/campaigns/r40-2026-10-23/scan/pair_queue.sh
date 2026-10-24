#!/bin/bash
# Even replies for 46's two short children whose odd obligations are all N.
for c in "16 20 46" "16 40 46 60"; do
  log="pair_any_$(echo $c | tr ' ' '-').log"
  echo "$(date '+%F %T') start" >> "$log"
  nice -n 10 /usr/bin/python3 pair_search_any.py $c --p-table --ncache-mb 8192 --threads 10 \
      --max-states 150000000 --timeout 600 >> "$log" 2>&1
  rc=$?
  echo "$(date '+%F %T') end (exit $rc)" >> "$log"
done
