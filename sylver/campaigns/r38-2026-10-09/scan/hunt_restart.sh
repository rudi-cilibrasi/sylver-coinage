#!/bin/sh
# Restart the retry hunt on the fixed hunt.py at a reply boundary: wait until its reply in progress
# is logged, then stop its whole process group (hunt_retry.sh, PGID 3777433: the driver, python and
# the solve it has just begun) and run it again.
cd "$(dirname "$0")"
n=$(wc -l < hunt.jsonl)
while [ "$(wc -l < hunt.jsonl)" -le "$n" ] && kill -0 14494 2>/dev/null; do sleep 15; done
kill -TERM -3777433 2>/dev/null
while kill -0 14494 2>/dev/null; do sleep 1; done
echo "$(date +%T) restart retry hunt (cap 1.6e9; partner witnesses outside the queue are logged; timer no longer shadows start)" >> hunt.log
nice -n 10 python3 hunt.py 1600000000 --retry-capped >> hunt.log 2>&1
echo "$(date +%T) retry hunt done" >> hunt.log
