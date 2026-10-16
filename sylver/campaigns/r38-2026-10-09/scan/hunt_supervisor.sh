#!/bin/sh
# The reply-38 hunt on 72's open children with kunz_pt (sylver/kunz_solver.cpp --p-table): first the
# replies the old engine capped (--retry-capped), then fresh replies, both --balance. Each phase
# writes its python PID to hunt.pid (memguard.sh and witness_watch.sh follow it). A phase is skipped
# once every open child has a witness.
cd "$(dirname "$0")"
export HUNT_ENGINE=kunz_pt HUNT_NCACHE_MB=16384 HUNT_TIMEOUT=10800 HUNT_THREADS=10 HUNT_MIN_START_GB=24
open_children() {
  python3 -c "
import json
rows = [json.loads(l) for l in open('hunt.jsonl')]
won = {tuple(r['child']) for r in rows if r['outcome'] == 'P'}
print(len({(16, 38, 68, 72), (16, 38, 72, 78), (16, 38, 72, 100), (16, 38, 72, 116)} - won))"
}
for phase in "--retry-capped --balance" "--balance"; do
  if [ "$(open_children)" = 0 ]; then
    echo "$(date +%T) every open child of 72 has a witness" >> hunt.log
    exit 0
  fi
  echo "$(date +%T) hunt phase '$phase' on kunz_pt (16 GB N-cache, 3 h per reply, 10 threads, 24 GB to start)" >> hunt.log
  nice -n 10 python3 hunt.py 1200000000 $phase >> hunt.log 2>&1 &
  echo $! > hunt.pid
  wait $!
done
echo "$(date +%T) kunz_pt hunt done" >> hunt.log
