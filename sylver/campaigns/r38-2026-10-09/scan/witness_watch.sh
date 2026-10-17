#!/bin/sh
# Finish (and so notify) when the hunt logs a new witness (more than $1 WITNESS lines, default 5),
# or when no hunt (hunt.pid) has run for ten minutes.
cd "$(dirname "$0")"
seen=${1:-5}
idle=0
while [ "$(grep -c '^WITNESS' hunt.log)" -le "$seen" ] && [ $idle -lt 10 ]; do
  if kill -0 "$(cat hunt.pid 2>/dev/null)" 2>/dev/null; then idle=0; else idle=$((idle + 1)); fi
  sleep 60
done
grep '^WITNESS' hunt.log | tail -n +"$((seen + 1))"
if [ $idle -ge 10 ]; then echo "no hunt running"; fi
exit 0
