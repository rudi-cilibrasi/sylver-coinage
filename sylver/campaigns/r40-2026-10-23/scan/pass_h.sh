#!/bin/bash
# Pass H: below 90, 82 and 86 are the answers a = 2 mod 4 still open. Pass A (screen.py, 30 minutes or 100M
# P-positions each) left 16 of 86's odd obligations and 15 of 82's unclassified, and pass C was stopped as it began
# 86, before it classified any of them. This waits for B66's evidence collection and the alternative-witness sizing to end (collect.py and
# size_alt.sh, PIDs $1 and $2), then sweeps those obligations with kunz_pt --p-table --stop-at-p and an 800M cap,
# 4 hours each, as pass C did. A P row refutes that answer; if every row is N, its odd obligations all lead to N and
# its even side decides. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for collect.py ($1) and size_alt.sh ($2) to end" >> pass_h.log
while kill -0 "$1" 2>/dev/null || kill -0 "$2" 2>/dev/null; do sleep 10; done

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

run() {   # tag, odd list, hours, position...
  local tag=$1 list=$2 hours=$3; shift 3
  local cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list $list $*"
  echo "$(date '+%F %T') start ($cmd; ${hours} h)" >> "deep_$tag.err"
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_h.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_h.log
}

run 86 73,77,81,85,89,93,97,101,105,109,113,117,121,125,133,141 4 16 40 86
run 82 71,75,79,83,87,91,95,99,103,107,111,115,119,127,135 4 16 40 82
echo "$(date '+%F %T') pass H end" >> pass_h.log
