#!/bin/bash
# Cheaper finite witnesses for B66={16,40,44,66}'s obligation 70: its witness 273 (the resolver's first P, in Frobenius
# order) needs 507,780,524 states alone, beyond a native replay on this host. This classifies every later odd reply up
# to 801 in the same order (kunz_pt --p-table, no stop at P, 8 threads, 4 GB N-cache, 300M cap, 2 hours) beside
# collect.py, so each P reply found can be sized alone. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
list=$(/usr/bin/python3 alt_list.py 273 801 16 40 44 66 70)
echo "$(date '+%F %T') start ($(tr ',' '\n' <<< "$list" | wc -l) replies)" >> alt_70.err
nice -n 10 ./kunz_pt --p-table --ncache-mb 4096 --threads 8 --max-states 300000000 --odd-list "$list" 16 40 44 66 70 \
    > alt_70.out 2>> alt_70.err &
pid=$!
start=$(date +%s)
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then echo "$(date '+%F %T') stopping: MemAvailable $avail kB" >> alt_70.err; kill $pid; break; fi
  if [ $(( $(date +%s) - start )) -ge 7200 ]; then echo "$(date '+%F %T') stopping: 2 hours" >> alt_70.err; kill $pid; break; fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc; $(grep -c '^move=' alt_70.out) classified; P: $(awk '$2 == "P" {printf "%s ", $1}' alt_70.out)" >> alt_70.err
