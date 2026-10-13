#!/bin/sh
# Odd children next: after the even sweeps (child_queue3.sh, PID 3830329), the odd children of
# 109, 117 and 125 one sweep at a time (250M-state cap, about 6 GB beside the 1.6e9 retry hunt's
# 38 GB; 2 threads; at most 4 h each), resuming from child_16-38-W.jsonl.
cd "$(dirname "$0")"
while kill -0 3830329 2>/dev/null; do sleep 30; done
for w in 109 117 125; do
  echo "$(date +%T) start odd child sweep $w" >> child_sweep.log
  timeout 14400 nice -n 10 python3 child_sweep.py $w --parity odd --max-states 250000000 --threads 2 >> child_sweep_$w.out 2>&1
  echo "$(date +%T) end odd child sweep $w rc=$?" >> child_sweep.log
done
echo "odd child sweeps done" >> child_sweep.log
