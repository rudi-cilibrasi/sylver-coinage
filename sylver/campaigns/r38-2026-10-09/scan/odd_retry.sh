#!/bin/sh
# Retry the odd candidates that stopped at the 1.7B cap, one at a time with a 2.1B cap.
cd "$(dirname "$0")"
until grep -q "queue done" odd_queue.log; do sleep 30; done
for m in 109 117 125; do
  if grep -q "^move=$m " odd_queue.out odd_retry.out 2>/dev/null; then continue; fi
  echo "$(date +%T) retry $m" >> odd_retry.log
  /usr/bin/time -v ./kunz --threads 8 --stop-at-p --max-states 2100000000 --memo-stats --odd-list $m 16 38 >> odd_retry.out 2> odd_retry_$m.err
  echo "$(date +%T) end $m rc=$?" >> odd_retry.log
  if grep -q "^move=$m P" odd_retry.out; then echo "ANSWER $m" >> odd_retry.log; break; fi
done
echo "retry done" >> odd_retry.log
