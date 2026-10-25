#!/bin/bash
# Once the odd-answer sweep (odd59.sh, its kunz_pt PID $1) has ended, collect B78's evidence: its move 20 by the
# reply 46 to Q (no odd reply up to 601 wins there: b78_finite_20.out, b78_finite_20b.out), 34 by 93 and 46 by 37
# (b78_finite_34.out, b78_finite_46.out), the rest from resolve_16-36-40-78.jsonl and the verified odd sweep.
# Stops collect.py if MemAvailable falls below 15 GB.
while kill -0 "$1" 2>/dev/null; do sleep 30; done
until grep -q ' exit ' odd_answers3.err; do sleep 10; done
echo "$(date '+%F %T') start" > collect_B78.log
THREADS=8 nice -n 10 /usr/bin/python3 collect.py resolve_16-36-40-78.jsonl \
    '{"20": [46, "Q"], "34": [93, "finite"], "46": [37, "finite"]}' 16 36 40 78 >> collect_B78.log 2>&1 &
pid=$!
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> collect_B78.log
    for p in $(tree $pid); do kill $p 2>/dev/null; done
    break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> collect_B78.log
