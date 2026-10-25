#!/bin/bash
# B78's certificates and replays, once collect.py has written its evidence (queue_b78.sh, in the scratch
# directory SRC = $1): copy collect_B78.log and evidence_16-36-40-78.json here, then replay.py, which runs the
# destinations up to 150M states two at a time within 22 GiB (native and Python), then the larger ones (90,
# 102 and 86) one at a time, native then sequential Kunz. Stops the replays if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
SRC=$1
until grep -q ' exit ' "$SRC/collect_B78.log"; do sleep 30; done
if ! grep -q ' exit 0$' "$SRC/collect_B78.log"; then
  echo "$(date '+%F %T') collect did not exit 0; not replaying" >> replay_B78.log; exit 1
fi
cp "$SRC/collect_B78.log" "$SRC/evidence_16-36-40-78.json" .
echo "$(date '+%F %T') start" >> replay_B78.log
REPLAY_MAX_JOBS=2 REPLAY_BUDGET_GIB=22 nice /usr/bin/python3 replay.py evidence_16-36-40-78.json b78_ "$(cd .. && pwd)" B78 \
    >> replay_B78.log 2>&1 &
pid=$!
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> replay_B78.log
    for p in $(tree $pid); do kill $p 2>/dev/null; done
    break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> replay_B78.log
