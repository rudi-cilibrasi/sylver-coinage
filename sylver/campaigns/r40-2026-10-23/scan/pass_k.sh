#!/bin/bash
# Pass K: is 82's child {16,40,60,82} P? Pass J's resolver found its 30 odd obligations all N ('short: needs even',
# October 27, 12:10), so it is P exactly when its 42 even obligations all lead to N too, and then 82 fails by 60.
# This stops pass J's even_resolver.py (PID $1; pass J then logs its exit and ends) during its row for 82's 68,
# which it can redo later, and resolves {16,40,60,82}'s even obligations as pass E did {16,40,66,76}'s, 16 hours at
# most. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
if kill -0 "$1" 2>/dev/null; then
  kill -STOP "$1"                           # so it starts no new kunz_pt while its children are found
  kids=$(ps -o pid= --ppid "$1")
  kill $kids 2>/dev/null
  kill -TERM "$1"; kill -CONT "$1"
  echo "$(date '+%F %T') stopped here by pass_k.sh (even_resolver.py $1 and" $kids"), during 82's 68: {16,40,60,82} first" >> eighty2.log
  echo "$(date '+%F %T') stopped even_resolver.py $1 and" $kids >> pass_k.log
fi
while kill -0 "$1" 2>/dev/null; do sleep 1; done

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

cmd="python3 even_resolver.py --position 16 40 60 82 --p-table --ncache-mb 8192 --threads 10 --short-first --max-states 400000000 --timeout 1200"
echo "$(date '+%F %T') start ($cmd; 16 h)" >> pass_k.log
nice -n 10 $cmd >> resolve_16-40-60-82.log 2>&1 &
pid=$!
memguard $pid 16 pass_k.log
wait $pid
rc=$?
echo "$(date '+%F %T') even_resolver.py exit $rc; $(tail -1 resolve_16-40-60-82.log)" >> pass_k.log
