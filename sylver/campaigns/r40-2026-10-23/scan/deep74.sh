#!/bin/bash
# After short_route.sh (PID $1) stops at 78: unless a short child of 74 was found P, look for even
# replies (pair_search_any.py) from the three unresolved children of {16,28,40,74} (29 of its 32
# obligations resolved by the short-child test), then resume the short-child route at 78.
while kill -0 "$1" 2>/dev/null; do sleep 30; done
found=$(/usr/bin/python3 -c "
import re
cur, found = None, False
for line in open('test_children.log'):
    m = re.search(r'test child \{16,40,74\}\+(\d+) start', line)
    if m: cur = m.group(1)
    elif cur and line.startswith('summary:') and \"'short: needs even': 0, 'open': 0\" in line: found = True
print(found)")
echo "$(date '+%F %T') deep74 start (a P child of 74 found: $found)" >> deep74.log
if [ "$found" != True ]; then
  for c in "16 28 34 40 74" "16 28 40 42 74" "16 28 40 74 98"; do
    log="pair_any_$(echo $c | tr ' ' '-').log"
    echo "$(date '+%F %T') start" >> "$log"
    nice -n 10 /usr/bin/python3 pair_search_any.py $c --p-table --ncache-mb 8192 --threads 10 \
        --max-states 150000000 --timeout 600 >> "$log" 2>&1
    rc=$?
    echo "$(date '+%F %T') end (exit $rc)" >> "$log"
    echo "$(date '+%F %T') pair search {$c} end (exit $rc)" >> deep74.log
  done
fi
./short_route.sh 78 82 86
echo "$(date '+%F %T') deep74 end" >> deep74.log
