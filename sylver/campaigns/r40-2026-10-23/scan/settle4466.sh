#!/bin/bash
# Is {16,40,44,66} P? Its short-first test (resolve_16-40-44-66.jsonl) resolved 31 of its 34 obligations; the
# children of the other three (36, 90, 134) are long, and their odd sweeps gave up. Look for an even reply
# from each (pair_search_any.py). If all three have one, {16,40,44,66} is P, and 66 fails.
for c in "16 36 40 44 66" "16 40 44 66 90" "16 40 44 66 134"; do
  log="pair_any_$(echo $c | tr ' ' '-').log"
  echo "$(date '+%F %T') start" >> "$log"
  nice -n 10 /usr/bin/python3 pair_search_any.py $c --p-table --ncache-mb 8192 --threads 10 \
      --max-states 150000000 --timeout 600 >> "$log" 2>&1
  rc=$?
  echo "$(date '+%F %T') end (exit $rc)" >> "$log"
  echo "$(date '+%F %T') pair search {$c} end (exit $rc)" >> settle4466.log
done
