#!/bin/bash
# Pass F. The case split: 76 = 16+16+44, so {16,40,66,76}+44 = X = {16,40,44,66}; if every even obligation of
# {16,40,66,76} other than 44 is N, then 66 is N whether X is P or N. Pass E's resolve of {16,40,66,76} left some of
# those open (the resolver gives up after four 20-minute batch timeouts). This waits for that resolve to end
# (pass_e.log), stops pass E there (pass_e.sh, PID $1: it would go on to resolve {16,40,66,84}) so that one solver
# runs at a time, then reruns each open row with kunz_pt --p-table --stop-at-p and an 800M cap: its skipped moves
# first, then the moves the resolver never reached (pass_f_lists.py), 4 hours each. If a row is still unresolved
# after that, it goes on with the same case split through {16,40,66,84}, then {16,40,66,116} (even_resolver.py, 10 h
# each). Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
E_SH=$1
echo "$(date '+%F %T') waiting for pass E's resolve of {16 40 66 76} to end" >> pass_f.log
while kill -0 "$E_SH" 2>/dev/null && ! grep -q -F 'resolve {16 40 66 76} end' pass_e.log; do sleep 5; done
if kill -0 "$E_SH" 2>/dev/null; then
  kill -STOP "$E_SH"
  kids=$(ps -o pid= --ppid "$E_SH")
  kill $kids 2>/dev/null
  kill -TERM "$E_SH"; kill -CONT "$E_SH"
  echo "$(date '+%F %T') stopped pass E after: $(grep -F 'resolve {16 40 66 76} end' pass_e.log) (killed pass_e.sh $E_SH and $kids)" >> pass_f.log
  echo "$(date '+%F %T') stopped here by pass_f.sh" >> pass_e.log
fi
while kill -0 "$E_SH" 2>/dev/null; do sleep 5; done

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
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_f.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_f.log
  [ -n "$p" ]
}

resolve() {   # hours, position...
  local hours=$1; shift
  local tag; tag=$(tr ' ' '-' <<< "$*")
  echo "$(date '+%F %T') resolve {$*} start (${hours} h)" >> pass_f.log
  nice -n 10 /usr/bin/python3 even_resolver.py --position "$@" --p-table --ncache-mb 8192 --threads 10 --short-first \
      --max-states 400000000 --timeout 1200 >> "resolve_$tag.log" 2>&1 &
  local pid=$!
  memguard $pid "$hours" "resolve_$tag.log"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') resolve {$*} end: exit $rc; $(grep -F 'summary:' "resolve_$tag.log" | tail -1)" >> pass_f.log
}

lists=$(/usr/bin/python3 pass_f_lists.py 16 40 66 76)
echo "$(date '+%F %T') open rows of {16 40 66 76}: $(tr '\n' ' ' <<< "$lists")" >> pass_f.log
left=0
while read -r e list <&3; do
  [ -n "$e" ] || continue
  run "76+$e" "$list" 4 16 40 66 76 "$e" || left=$((left + 1))
done 3<<< "$lists"
echo "$(date '+%F %T') {16 40 66 76}: $left open row(s) still unresolved" >> pass_f.log
if [ "$left" -gt 0 ]; then
  resolve 10 16 40 66 84
  resolve 10 16 40 66 116
fi
echo "$(date '+%F %T') pass F end" >> pass_f.log
