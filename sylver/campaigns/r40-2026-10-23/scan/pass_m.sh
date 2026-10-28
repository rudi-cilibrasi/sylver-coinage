#!/bin/bash
# Pass M: {16,40,60,82}'s obligations that pass L leaves open, on odd replies above 401, as pass G did. Pass L found
# all 200 odd replies up to 401 to {16,40,60,82,90} N, and a long position can need a large odd winner (pass G:
# 126 by 553, 36 by 447, 90 by 463). This waits for pass_l.sh (PID $1) to end, then runs kunz_pt --p-table
# --stop-at-p (800M cap) on 403..1601 (child Frobenius number at most 1751, under kunz_pt's coordinate limit) for
# each of 90, 150 and 166 whose pass L output has no P row, 4 hours each. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for pass_l.sh $1 to end" >> pass_m.log
while kill -0 "$1" 2>/dev/null; do sleep 5; done
echo "$(date '+%F %T') pass L ended: $(tail -1 pass_l.log)" >> pass_m.log

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
  echo "$(date '+%F %T') $tag start: {$*} + 403..1601 (${hours} h)" >> pass_m.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_m.log
}
has_p() { [ -f "$1" ] && awk '/^move=/ && $2 == "P" {f = 1} END {exit !f}' "$1"; }

big=$(seq -s, 403 2 1601)
for e in 90 150 166; do
  if has_p "deep_82+60+$e.out"; then
    echo "$(date '+%F %T') 82+60+$e: pass L found a P reply" >> pass_m.log
  else
    run "82+60+${e}x" "$big" 4 16 40 60 82 "$e"
  fi
done
echo "$(date '+%F %T') pass M end" >> pass_m.log
