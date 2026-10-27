#!/bin/bash
# Pass E. Pass D found 66+76's skipped obligation 75 and 66+84's four (67, 71, 79, 87) N, so {16,40,66,76} and
# {16,40,66,84} are odd-complete: short P-candidates whose being P would refute 66 certifiably. This waits for
# pass D's 66+116 to end (pass_d.log), stops pass D there (pass_d.sh, PID $1) so that one solver runs at a time, then:
#   1. if 116's four skipped obligations were all N, its five never tried (the resolver gave up after four skips:
#      75, 87, 95, 83, 103, in its Frobenius order), with kunz_pt --p-table --stop-at-p as in pass D;
#   2. even_resolver.py --position on 66+76, then 66+84 (then 66+116, if it is odd-complete): each even obligation
#      of the candidate, short ones first (resolve_16-40-66-<e>.jsonl), 10 hours each at most;
#   3. pass D's Y part (Y = {16,40,52,66}: its seven long opens), which pass D did not reach.
# Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
D_SH=$1
echo "$(date '+%F %T') waiting for pass D's 66+116 to end" >> pass_e.log
while kill -0 "$D_SH" 2>/dev/null && ! grep -q -F '66+116 end' pass_d.log; do sleep 5; done
if kill -0 "$D_SH" 2>/dev/null; then
  kill -STOP "$D_SH"
  kids=$(ps -o pid= --ppid "$D_SH")
  kill $kids 2>/dev/null
  kill -TERM "$D_SH"; kill -CONT "$D_SH"
  echo "$(date '+%F %T') stopped pass D after: $(grep -F '66+116 end' pass_d.log) (killed pass_d.sh $D_SH and $kids)" >> pass_e.log
  echo "$(date '+%F %T') stopped here by pass_e.sh (its Y part runs in pass E)" >> pass_d.log
fi
while kill -0 "$D_SH" 2>/dev/null; do sleep 5; done

memguard() {   # pid, hours, log: kill the process tree on low memory or at the time limit
  local pid=$1 hours=$2 log=$3 start p
  start=$(date +%s)
  tree() { local q; for q in $(ps -o pid= --ppid "$1"); do tree "$q"; done; echo "$1"; }
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
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_e.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_e.log
}

resolve() {   # hours, position...
  local hours=$1; shift
  local tag; tag=$(tr ' ' '-' <<< "$*")
  echo "$(date '+%F %T') resolve {$*} start (${hours} h)" >> pass_e.log
  nice -n 10 /usr/bin/python3 even_resolver.py --position "$@" --p-table --ncache-mb 8192 --threads 10 --short-first \
      --max-states 400000000 --timeout 1200 >> "resolve_$tag.log" 2>&1 &
  local pid=$!
  memguard $pid "$hours" "resolve_$tag.log"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') resolve {$*} end: exit $rc; $(grep -F 'summary:' "resolve_$tag.log" | tail -1)" >> pass_e.log
}

if [ "$(grep -c '^move=.* N ' deep_66+116.out)" -eq 4 ]; then
  run 66+116b 75,87,95,83,103 2 16 40 66 116
fi
resolve 10 16 40 66 76
resolve 10 16 40 66 84
if [ "$(grep -c '^move=.* N ' deep_66+116.out)" -eq 4 ] && [ "$(grep -c '^move=.* N ' deep_66+116b.out)" -eq 5 ]; then
  resolve 10 16 40 66 116
fi
run Y+58 103,105,107,111 2 16 40 52 58 66
run Y+60 65,73,77,95 2 16 40 52 60 66
run Y+76 93,99,113,125 2 16 40 52 66 76
run Y+86 137,139,141,143 2 16 40 52 66 86
run Y+90 83,109,115,127 2 16 40 52 66 90
run Y+110 103,107,111,115 2 16 40 52 66 110
run Y+142 101,109,131,139 2 16 40 52 66 142
echo "$(date '+%F %T') pass E end" >> pass_e.log
