#!/bin/bash
# Pass N: 86's eight open odd obligations, 105, 109, 113, 117, 121, 125, 133 and 141. Pass H classified 73 to 101 and
# stopped at its 4-hour limit during 105; pass I's runs on these were stopped before they wrote a row. 82 now fails
# by 60 ({16,40,60,82} P by search), so 86 is the one answer a = 2 (mod 4) below 90 still open. This runs kunz_pt as
# pass C did (--p-table --stop-at-p, 800M cap) on each obligation alone, 3 hours each, so that one hard obligation
# does not hold up the rest: deep_86+<w>.out and .err. A P row means 86 fails by w. Stopped if MemAvailable falls
# below 15 GB.
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

run() {   # tag, odd list, hours, position...
  local tag=$1 list=$2 hours=$3; shift 3
  local cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list $list $*"
  echo "$(date '+%F %T') start ($cmd; ${hours} h)" >> "deep_$tag.err"
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_n.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  echo "$(date '+%F %T') $tag end: exit $rc; $(grep '^move=' "deep_$tag.out" || echo 'no row')" >> pass_n.log
}

for w in 105 109 113 117 121 125 133 141; do
  run "86+$w" "$w" 3 16 40 86
  if awk '/^move=/ && $2 == "P" {f = 1} END {exit !f}' "deep_86+$w.out"; then
    echo "$(date '+%F %T') 86 fails by $w; the rest are not needed" >> pass_n.log
    break
  fi
done
echo "$(date '+%F %T') pass N end" >> pass_n.log
