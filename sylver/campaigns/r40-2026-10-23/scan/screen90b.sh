#!/bin/bash
# Pass B: the odd obligations of the answers a = 2 mod 4 from 90 to 198 that the light sweep (screen90.sh) left
# open, again with pass A's settings: kunz_pt --p-table, an 8 GiB N-cache, 10 threads, a cap of 100M P-positions
# and 30 minutes each. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') start" >> screen90b.log
nice -n 10 /usr/bin/python3 screen.py --odd --p-table --ncache-mb 8192 --threads 10 --max-states 100000000 \
    --timeout 1800 --amin 90 --amax 198 --redo-partial >> screen90b.log 2>&1 &
pid=$!
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> screen90b.log
    for p in $(tree $pid); do kill $p 2>/dev/null; done
    break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> screen90b.log
