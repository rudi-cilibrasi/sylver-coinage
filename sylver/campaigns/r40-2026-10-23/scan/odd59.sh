#!/bin/bash
# The odd answers to 40 from 59 on: is {16,40,a} P for some odd a? (odd_answers2, one hour at a 300M cap, reached
# 59.) One shared memo, stopping at the first P, with a cap of 700M P-positions (about 17 GB, plus the 8 GB
# N-cache). Stopped if MemAvailable falls below 15 GB, or after 6 hours.
list=$(seq -s, 59 2 99)
cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 700000000 --odd-list $list 16 40"
echo "$(date '+%F %T') start ($cmd)" >> odd_answers3.err
nice -n 10 $cmd > odd_answers3.out 2>> odd_answers3.err &
pid=$!
start=$(date +%s)
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> odd_answers3.err; kill $pid; break
  fi
  if [ $(( $(date +%s) - start )) -ge 21600 ]; then
    echo "$(date '+%F %T') stopping: six hours" >> odd_answers3.err; kill $pid; break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> odd_answers3.err
