#!/bin/sh
# {16,38}'s open odd candidates, each alone with a large memo; stop at the first P (an answer to 38).
cd "$(dirname "$0")"
for m in 85 93 101 87 109 117 125; do
  if grep -q "^move=$m " odd_queue.out 2>/dev/null; then continue; fi
  echo "$(date +%T) start $m" >> odd_queue.log
  /usr/bin/time -v ./kunz --threads 8 --stop-at-p --max-states 1700000000 --memo-stats --odd-list $m 16 38 >> odd_queue.out 2> odd_queue_$m.err
  echo "$(date +%T) end $m rc=$?" >> odd_queue.log
  if grep -q "^move=$m P" odd_queue.out; then echo "ANSWER $m" >> odd_queue.log; break; fi
done
echo "queue done" >> odd_queue.log
