#!/bin/sh
# Restart the retry hunt with 10 solver threads at a reply boundary: wait until its reply in
# progress is logged, stop its process group (hunt_restart.sh, PGID 83196: driver, python 98379
# and the solve it has just begun), and run it again with HUNT_THREADS=10.
cd "$(dirname "$0")"
n=$(wc -l < hunt.jsonl)
while [ "$(wc -l < hunt.jsonl)" -le "$n" ] && kill -0 98379 2>/dev/null; do sleep 15; done
kill -TERM -83196 2>/dev/null
while kill -0 98379 2>/dev/null; do sleep 1; done
echo "$(date +%T) restart retry hunt with 10 solver threads (HUNT_THREADS=10)" >> hunt.log
HUNT_THREADS=10 nice -n 10 python3 hunt.py 1600000000 --retry-capped >> hunt.log 2>&1
echo "$(date +%T) retry hunt done" >> hunt.log
