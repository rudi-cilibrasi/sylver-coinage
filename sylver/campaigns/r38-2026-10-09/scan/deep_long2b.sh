#!/bin/sh
# Pass 2, reordered on 2026-10-12: after 46 (already running), the two other candidates new to pass 2.
cd "$(dirname "$0")"
while kill -0 3773552 2>/dev/null; do sleep 30; done   # the running sweep of 46
echo "$(date +%T) end 46 (driver replaced; see deep_long2.out)" >> deep_long2.log
echo "$(date +%T) start 234" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 42 --also 71,75,85,83 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 234 >> deep_long2.out 2>&1
echo "$(date +%T) end 234 rc=$?" >> deep_long2.log
echo "$(date +%T) start 250" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 39 --also 71,79,85,93 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 250 >> deep_long2.out 2>&1
echo "$(date +%T) end 250 rc=$?" >> deep_long2.log
echo "deep long 2b done (234, 250); the 24 candidates of pass 1 are still to do" >> deep_long2.log
