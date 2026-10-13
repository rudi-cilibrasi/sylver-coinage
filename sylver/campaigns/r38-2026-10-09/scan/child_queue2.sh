#!/bin/sh
# Child sweeps of the hard odd obligations 117 and 125 of {16,38}, in parallel (200M-state cap,
# 2 threads, 3 h each); 109's sweep follows the pair probes ({16,38,117}+125, then {16,38,109}+117).
cd "$(dirname "$0")"
sweep() {
  echo "$(date +%T) start child sweep $1" >> child_sweep.log
  timeout 10800 nice -n 10 python3 child_sweep.py $1 --max-states 200000000 --threads 2 >> child_sweep_$1.out 2>&1
  echo "$(date +%T) end child sweep $1 rc=$?" >> child_sweep.log
}
sweep 117 &
sweep 125 &
while kill -0 3743905 2>/dev/null; do sleep 30; done   # the running {16,38,117}+125 probe
echo "$(date +%T) probe 117 on {16,38,109}" >> pair_hard.log
/usr/bin/time -f "%e s %M KB" nice -n 10 ./kunz --threads 2 --stop-at-p --max-states 400000000 --odd-list 117 16 38 109 >> pair_hard.log 2>&1
sweep 109
wait
echo "child sweeps done" >> child_sweep.log
