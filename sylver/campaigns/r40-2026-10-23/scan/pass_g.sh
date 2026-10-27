#!/bin/bash
# Pass G. Two routes refute 66, and each is held up by long positions with no odd winner up to 401:
#   the case split through {16,40,66,76} (every even obligation but 44 must be N; 126 and 150 are open: pass F
#   found all 135 odd replies to {16,40,66,76,126} from 107 to 401 N), and
#   X = {16,40,44,66} P (its open obligations 36, 90, 134: long children; X+36 has all 200 odd replies up to 401 N).
# A long position can need a large odd winner (RESEARCH: {16,20,34,58} only by 291; a long reply 12 only by 825), so
# this searches odd replies above 401, up to 1601 (child Frobenius below 1800, under kunz_pt's coordinate limit
# 127*16). It waits for pass F's 76+150 to end (pass_f.log), stops pass F (pass_f.sh, PID $1) before its resolve of
# {16,40,66,84}, then runs kunz_pt --p-table --stop-at-p (800M cap) on:
#   1. 76+126 on 403..1601; 2. 76+150 on 403..1601 if pass F found no P reply for it;
#   3. X+90 and X+134 on their skipped and never-reached odd replies up to 401 (pass_f_lists.py 16 40 44 66);
#   4. X+36 on 403..1601; 5. X+90 and X+134 on 403..1601 if still open.
# Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
F_SH=$1
echo "$(date '+%F %T') waiting for pass F's 76+150 to end" >> pass_g.log
while kill -0 "$F_SH" 2>/dev/null && ! grep -q -F '76+150 end' pass_f.log; do sleep 5; done
tree() { local q; for q in $(ps -o pid= --ppid "$1"); do tree "$q"; done; echo "$1"; }
if kill -0 "$F_SH" 2>/dev/null; then
  kill -STOP "$F_SH"
  kids=$(for q in $(ps -o pid= --ppid "$F_SH"); do tree "$q"; done)
  kill $kids 2>/dev/null
  kill -TERM "$F_SH"; kill -CONT "$F_SH"
  echo "$(date '+%F %T') stopped pass F after: $(grep -F '76+150 end' pass_f.log) (killed pass_f.sh $F_SH and" $kids")" >> pass_g.log
  echo "$(date '+%F %T') stopped here by pass_g.sh" >> pass_f.log
fi
while kill -0 "$F_SH" 2>/dev/null; do sleep 5; done

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

run() {   # tag, odd list, hours, position...: succeeds iff a P reply was found
  local tag=$1 list=$2 hours=$3; shift 3
  local cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list $list $*"
  echo "$(date '+%F %T') start ($cmd; ${hours} h)" >> "deep_$tag.err"
  echo "$(date '+%F %T') $tag start: {$*} + ${list:0:40}... ($(tr ',' '\n' <<< "$list" | wc -l) moves, ${hours} h)" >> pass_g.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_g.log
  [ -n "$p" ]
}

has_p() { [ -n "$(awk '/^move=/ && $2 == "P"' "$1" 2>/dev/null)" ]; }

big=$(seq -s, 403 2 1601)
run 76+126x "$big" 4 16 40 66 76 126
has_p deep_76+150.out || run 76+150x "$big" 4 16 40 66 76 150
xlists=$(/usr/bin/python3 pass_f_lists.py 16 40 44 66)
while read -r e list <&3; do
  [ -n "$list" ] || continue
  run "X+$e" "$list" 3 16 40 44 66 "$e"
done 3<<< "$xlists"
run X+36x "$big" 4 16 36 40 44 66
has_p deep_X+90.out || run X+90x "$big" 4 16 40 44 66 90
has_p deep_X+134.out || run X+134x "$big" 4 16 40 44 66 134
echo "$(date '+%F %T') pass G end" >> pass_g.log
