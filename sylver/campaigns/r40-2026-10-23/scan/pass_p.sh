#!/bin/bash
# Pass P: is 86's child {16,40,68,86} P? Pass O's resolver found its 32 odd obligations all N ('short: needs even',
# October 28, 20:03), so it is P exactly when its 45 even obligations all lead to N too, and then 86 fails by 68
# (and 68 by 86). This resolves {16,40,68,86}'s even obligations as pass K did {16,40,60,82}'s, 16 hours at most.
# Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1

tree() { local q; for q in $(ps -o pid= --ppid "$1"); do tree "$q"; done; echo "$1"; }
memguard() {   # pid, hours, log: kill the process tree on low memory or at the time limit
  local pid=$1 hours=$2 log=$3 start p
  start=$(date +%s)
  while kill -0 "$pid" 2>/dev/null; do
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [ "$avail" -lt 15728640 ]; then
      echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> "$log"
      for p in $(tree "$pid"); do kill "$p" 2>/dev/null; done; break
    fi
    if [ $(( $(date +%s) - start )) -ge $(( hours * 3600 )) ]; then
      echo "$(date '+%F %T') stopping: $hours hours" >> "$log"
      for p in $(tree "$pid"); do kill "$p" 2>/dev/null; done; break
    fi
    sleep 10
  done
}

cmd="python3 even_resolver.py --position 16 40 68 86 --p-table --ncache-mb 8192 --threads 10 --short-first --max-states 400000000 --timeout 1200"
echo "$(date '+%F %T') start ($cmd; 16 h)" >> pass_p.log
nice -n 10 $cmd >> resolve_16-40-68-86.log 2>&1 &
pid=$!
memguard $pid 16 pass_p.log
wait $pid
rc=$?
echo "$(date '+%F %T') even_resolver.py exit $rc; $(tail -1 resolve_16-40-68-86.log)" >> pass_p.log
