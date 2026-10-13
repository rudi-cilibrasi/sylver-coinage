#!/bin/sh
# After pass 2's fresh candidates (deep_long2b.sh, PID 3776302), retry the replies of 72's six open
# children that capped at 1e9, now at 1.6e9 states (about 38 GB), lowest Frobenius rank first.
cd "$(dirname "$0")"
while kill -0 3776302 2>/dev/null; do sleep 60; done
echo "$(date +%T) retry hunt (cap 1.6e9, the capped replies of 72's six open children)" >> hunt.log
nice -n 10 python3 hunt.py 1600000000 --retry-capped >> hunt.log 2>&1
echo "$(date +%T) retry hunt done" >> hunt.log
