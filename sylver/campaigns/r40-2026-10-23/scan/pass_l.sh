#!/bin/bash
# Pass L: pass K's open rows of {16,40,60,82}, as pass F did {16,40,66,76}'s. This waits for pass_k.sh (PID $1) to
# end. If every row of resolve_16-40-60-82.jsonl is then 'resolved' or 'open' (no row refutes {16,40,60,82}, and no
# grandchild needs its own resolve first), it reruns each open row with kunz_pt --p-table --stop-at-p and an 800M cap:
# its skipped moves first, then the moves the resolver never reached (pass_f_lists.py), 4 hours each. A P row there
# means {16,40,60,82,e} is N, so its obligation e is met. Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for pass_k.sh $1 to end" >> pass_l.log
while kill -0 "$1" 2>/dev/null; do sleep 5; done
echo "$(date '+%F %T') pass K ended: $(tail -1 pass_k.log)" >> pass_l.log

other=$(/usr/bin/python3 -c '
import json
latest = {}
for line in open("resolve_16-40-60-82.jsonl"):
    row = json.loads(line)
    latest[row["e"]] = row
print(" ".join("%d:%s" % (e, row["status"]) for e, row in sorted(latest.items()) if row["status"] not in ("resolved", "open")))
') || { echo "$(date '+%F %T') the row check failed" >> pass_l.log; exit 1; }
if [ -n "$other" ]; then
  echo "$(date '+%F %T') rows neither resolved nor open: $other; not rerunning the open rows" >> pass_l.log
  exit 0
fi

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
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_l.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_l.log
  [ -n "$p" ]
}

lists=$(/usr/bin/python3 pass_f_lists.py 16 40 60 82)
echo "$(date '+%F %T') open rows of {16 40 60 82}: $(tr '\n' ' ' <<< "$lists")" >> pass_l.log
left=0
while read -r e list <&3; do
  [ -n "$e" ] || continue
  run "82+60+$e" "$list" 4 16 40 60 82 "$e" || left=$((left + 1))
done 3<<< "$lists"
echo "$(date '+%F %T') {16 40 60 82}: $left open row(s) still unresolved" >> pass_l.log
echo "$(date '+%F %T') pass L end" >> pass_l.log
