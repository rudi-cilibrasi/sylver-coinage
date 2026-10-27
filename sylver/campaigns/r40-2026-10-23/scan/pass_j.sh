#!/bin/bash
# Pass J: 82's even side, if its last odd obligation 135 is N. Pass I (pass_i.sh, PID $1) runs 135 alone, then 86's
# leftovers. This waits for pass I's "82x end" line. If deep_82x.out has 135 N, every odd obligation of {16,40,82}
# is N (passes A, H and I), so 82 answers 40 exactly when every even obligation is N too, and that is the better
# use of the host than 86's leftovers: it stops pass I and its solver, adds the even rows that the new odd row
# settles (cross_rows.py), and runs even_resolver.py on 82's even obligations, the open short ones again first,
# then the long ones, 24 hours at most. Otherwise it leaves pass I to go on. Stopped if MemAvailable falls below
# 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for pass I's 82x end line" >> pass_j.log
while kill -0 "$1" 2>/dev/null && ! grep -q '82x end' pass_i.log; do sleep 5; done
if ! grep -q '^move=135 N' deep_82x.out; then
  echo "$(date '+%F %T') 135 is not N ($(cat deep_82x.out)); pass I goes on" >> pass_j.log; exit 0
fi
if kill -0 "$1" 2>/dev/null; then
  kill -STOP "$1"                           # so it starts nothing new while its children are found
  kids=$(ps -o pid= --ppid "$1")
  kill $kids 2>/dev/null
  kill -TERM "$1"; kill -CONT "$1"
  echo "$(date '+%F %T') stopped here by pass_j.sh (pass_i.sh $1 and $kids): 82 is odd-complete" >> pass_i.log
  echo "$(date '+%F %T') stopped pass_i.sh $1 and $kids" >> pass_j.log
fi
python3 cross_rows.py 82 --b66 >> cross_82.log
echo "$(date '+%F %T') cross_rows.py 82 --b66: $(wc -l < cross_82.log) rows in cross_82.log" >> pass_j.log

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

cmd="python3 even_resolver.py 82 --p-table --ncache-mb 8192 --threads 10 --short-first --redo-open --max-states 400000000 --timeout 1200"
echo "$(date '+%F %T') start ($cmd; 24 h)" >> pass_j.log
nice -n 10 $cmd >> eighty2.log 2>&1 &
pid=$!
memguard $pid 24 pass_j.log
wait $pid
rc=$?
echo "$(date '+%F %T') even_resolver.py exit $rc; $(tail -1 eighty2.log)" >> pass_j.log
