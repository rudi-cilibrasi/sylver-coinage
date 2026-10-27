#!/bin/bash
# Size the alternative witnesses alt68.sh and alt70.sh found for B66's obligations 68 and 70 (their first ones, 265
# and 273, need 679.7M and 507.8M states alone): each destination solved alone by kunz (4 threads, so the count is
# close to, not exactly, the sequential one collect.py takes), one at a time -> size_alt.log. Stopped below 15 GB.
cd "$(dirname "$0")" || exit 1
for dest in "16 40 44 66 68 291" "16 40 44 66 70 311" "16 40 44 66 70 287"; do
  start=$(date +%s)
  nice -n 10 ./kunz --threads 4 $dest > size_alt.tmp 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [ "$avail" -lt 15728640 ]; then echo "$(date '+%F %T') {$dest} stopping: MemAvailable $avail kB" >> size_alt.log; kill $pid; break; fi
    sleep 5
  done
  wait $pid
  rc=$?
  echo "$(date '+%F %T') {$dest} exit $rc $(( $(date +%s) - start )) s: $(head -c 200 size_alt.tmp)" >> size_alt.log
done
rm -f size_alt.tmp
