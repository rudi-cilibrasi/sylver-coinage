#!/bin/sh
# Even children first: the three child sweeps (109, 117, 125) in parallel over their even children
# only (200M-state cap, 2 threads, at most 3 h each), resuming from child_16-38-W.jsonl.
cd "$(dirname "$0")"
sweep() {
  echo "$(date +%T) start even child sweep $1" >> child_sweep.log
  timeout 10800 nice -n 10 python3 child_sweep.py $1 --parity even --max-states 200000000 --threads 2 >> child_sweep_$1.out 2>&1
  echo "$(date +%T) end even child sweep $1 rc=$?" >> child_sweep.log
}
sweep 109 &
sweep 117 &
sweep 125 &
wait
echo "even child sweeps done" >> child_sweep.log
