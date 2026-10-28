#!/bin/bash
# Pass O: 86's even side, after pass N (pass_n.sh, PID $1). If pass N found a P row, 86 fails and there is nothing
# to do. Otherwise this adds the even rows that pass N's odd rows and the known P-positions settle (cross_rows.py
# 86 --known), then runs even_resolver.py on 86's even obligations, 24 hours at most: the five open short ones again
# first (68, 100, 108, 132 and 140, each with four replies skipped on October 25), then the long ones, which have
# never been run. It stops at the first child that is short with every odd obligation N ('short: needs even'): that
# child may be P, which would refute 86 as {16,40,60,82} refuted 82, so it is tested next. Stopped if MemAvailable
# falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for pass_n.sh $1 to end" >> pass_o.log
while kill -0 "$1" 2>/dev/null; do sleep 5; done
echo "$(date '+%F %T') pass N ended: $(tail -1 pass_n.log)" >> pass_o.log
if grep -q 'fails by' pass_n.log; then
  echo "$(date '+%F %T') $(grep 'fails by' pass_n.log); 86's even side is not needed" >> pass_o.log
  exit 0
fi
python3 cross_rows.py 86 --known >> cross_86.log || { echo "$(date '+%F %T') cross_rows.py failed" >> pass_o.log; exit 1; }
echo "$(date '+%F %T') cross_rows.py 86 --known: $(wc -l < cross_86.log) rows in cross_86.log" >> pass_o.log

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

cmd="python3 even_resolver.py 86 --p-table --ncache-mb 8192 --threads 10 --short-first --redo-open --stop-at-needs-even --max-states 400000000 --timeout 1200"
echo "$(date '+%F %T') start ($cmd; 24 h)" >> pass_o.log
nice -n 10 $cmd >> eighty6.log 2>&1 &
pid=$!
memguard $pid 24 pass_o.log
wait $pid
rc=$?
echo "$(date '+%F %T') even_resolver.py exit $rc; $(tail -1 eighty6.log)" >> pass_o.log
