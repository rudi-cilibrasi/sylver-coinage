#!/bin/sh
# Finish (and so notify) when the hunt logs a new witness (there were 4 WITNESS lines), or when
# no hunt (hunt.pid) has run for ten minutes.
cd "$(dirname "$0")"
idle=0
while [ "$(grep -c '^WITNESS' hunt.log)" -le 4 ] && [ $idle -lt 10 ]; do
  if kill -0 "$(cat hunt.pid 2>/dev/null)" 2>/dev/null; then idle=0; else idle=$((idle + 1)); fi
  sleep 60
done
grep '^WITNESS' hunt.log | tail -n +5
[ $idle -ge 10 ] && echo "no hunt running"
