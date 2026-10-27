#!/bin/bash
# Pass C: the odd obligations of 66, 74, 86 and 82 that pass A (screen.py: 30 minutes or 100M P-positions each, in
# ascending order) left unclassified. kunz_pt --p-table on just those, one shared memo per answer, stopping at the
# first P, with a cap of 800M P-positions (about 19 GB, plus the 8 GB N-cache) and the hours given below.
# Stopped if MemAvailable falls below 15 GB. It first waits for pass B's next row (screen90b.log), then stops
# pass B (screen90b.sh, PIDs given as $1 and $2: the shell and its screen.py) so that one solver runs at a time.
cd "$(dirname "$0")" || exit 1
B_SH=$1; B_PY=$2
rows=$(wc -l < screen90b.log)
echo "$(date '+%F %T') waiting for pass B's next row (screen90b.log has $rows lines)" >> pass_c.log
while kill -0 "$B_SH" 2>/dev/null && [ "$(wc -l < screen90b.log)" -le "$rows" ]; do sleep 5; done
if kill -0 "$B_PY" 2>/dev/null; then
  kill -STOP "$B_PY"                        # so it starts no new kunz_pt while its children are found
  kids=$(ps -o pid= --ppid "$B_PY")
  kill $kids 2>/dev/null
  kill -TERM "$B_PY"; kill -CONT "$B_PY"
  echo "$(date '+%F %T') stopped pass B after its row: $(tail -1 screen90b.log) (killed screen.py $B_PY and $kids)" >> pass_c.log
fi
while kill -0 "$B_SH" 2>/dev/null; do sleep 5; done

run() {   # answer, its leftover odd obligations, hours
  local a=$1 list=$2 hours=$3
  local cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list $list 16 40 $a"
  echo "$(date '+%F %T') start ($cmd; ${hours} h)" >> "deep_$a.err"
  echo "$(date '+%F %T') $a start: $list (${hours} h)" >> pass_c.log
  nice -n 10 $cmd > "deep_$a.out" 2>> "deep_$a.err" &
  local pid=$! start
  start=$(date +%s)
  while kill -0 $pid 2>/dev/null; do
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [ "$avail" -lt 15728640 ]; then
      echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> "deep_$a.err"; kill $pid; break
    fi
    if [ $(( $(date +%s) - start )) -ge $(( hours * 3600 )) ]; then
      echo "$(date '+%F %T') stopping: $hours hours" >> "deep_$a.err"; kill $pid; break
    fi
    sleep 10
  done
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$a.err"
  local n p
  n=$(grep -c '^move=' "deep_$a.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$a.out")
  echo "$(date '+%F %T') $a end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_c.log
}

run 66 95,103,111 6
run 74 87,91,95,99,103,107,115,123 4
run 86 73,77,81,85,89,93,97,101,105,109,113,117,121,125,133,141 3
run 82 71,75,79,83,87,91,95,99,103,107,111,115,119,127,135 3
echo "$(date '+%F %T') pass C end" >> pass_c.log
