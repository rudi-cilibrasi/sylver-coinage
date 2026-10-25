#!/bin/bash
# A light odd screen of the answers a = 2 mod 4 from 90 to 398, alongside B78's replays: for each a,
# screen.py's odd stage (kunz_pt --p-table, stopping at the first P child) with a cap of 20M P-positions,
# a 1 GiB N-cache, 4 threads and five minutes. Stopped if MemAvailable falls below 17 GB, to leave the
# replays room.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') start" >> screen90.log
nice -n 10 /usr/bin/python3 screen.py --odd --p-table --ncache-mb 1024 --amin 90 --threads 4 \
    --max-states 20000000 --timeout 300 >> screen90.log 2>&1 &
pid=$!
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 17825792 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 17 GB" >> screen90.log
    for p in $(tree $pid); do kill $p 2>/dev/null; done
    break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> screen90.log
