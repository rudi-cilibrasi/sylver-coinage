#!/bin/bash
# Pass D: the moves that sixty6.sh and the October 23-24 resolver runs skipped (a batch timed out on them), each
# rerun alone with kunz_pt --p-table --stop-at-p, an 800M cap on P-positions (about 19 GB, plus the 8 GB N-cache)
# and the hours given below. A P child is the expensive kind, so a skipped move is the likeliest winning reply.
#   1. 66's three open SHORT children {16,40,66,e}, e = 76, 84, 116: if all the skipped odd obligations of one are N,
#      that child is odd-complete, a P-candidate (it needs only its even side) that would refute 66 certifiably.
#   2. The seven open LONG children of Y = {16,40,52,66} (66+52), searched on October 24 with only 100M and 300 s:
#      Y is P (so 66 fails) only if each of them is N, i.e. has a P odd reply.
# It first waits for sixty6.sh's next row (sixty6.log), then stops its even_resolver.py (PIDs given as $1 and $2:
# the shell and its python) so that one solver runs at a time; even_resolver.py resumes from even_66.jsonl later.
# Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
S_SH=$1; S_PY=$2
rows=$(wc -l < sixty6.log)
echo "$(date '+%F %T') waiting for sixty6's next row (sixty6.log has $rows lines)" >> pass_d.log
while kill -0 "$S_SH" 2>/dev/null && [ "$(wc -l < sixty6.log)" -le "$rows" ]; do sleep 5; done
if kill -0 "$S_PY" 2>/dev/null; then
  kill -STOP "$S_PY"                        # so it starts no new kunz_pt while its children are found
  kids=$(ps -o pid= --ppid "$S_PY")
  kill $kids 2>/dev/null
  kill -TERM "$S_PY"; kill -CONT "$S_PY"
  echo "$(date '+%F %T') stopped sixty6 after its row: $(tail -1 sixty6.log) (killed even_resolver.py $S_PY and $kids)" >> pass_d.log
fi
while kill -0 "$S_SH" 2>/dev/null; do sleep 5; done

run() {   # tag, odd list, hours, position...
  local tag=$1 list=$2 hours=$3; shift 3
  local cmd="./kunz_pt --p-table --ncache-mb 8192 --threads 10 --stop-at-p --max-states 800000000 --odd-list $list $*"
  echo "$(date '+%F %T') start ($cmd; ${hours} h)" >> "deep_$tag.err"
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_d.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$! start
  start=$(date +%s)
  while kill -0 $pid 2>/dev/null; do
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [ "$avail" -lt 15728640 ]; then
      echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> "deep_$tag.err"; kill $pid; break
    fi
    if [ $(( $(date +%s) - start )) -ge $(( hours * 3600 )) ]; then
      echo "$(date '+%F %T') stopping: $hours hours" >> "deep_$tag.err"; kill $pid; break
    fi
    sleep 10
  done
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_d.log
}

run 66+76 75 2 16 40 66 76
run 66+84 67,71,79,87 2 16 40 66 84
run 66+116 55,63,71,79 2 16 40 66 116
run Y+58 103,105,107,111 2 16 40 52 58 66
run Y+60 65,73,77,95 2 16 40 52 60 66
run Y+76 93,99,113,125 2 16 40 52 66 76
run Y+86 137,139,141,143 2 16 40 52 66 86
run Y+90 83,109,115,127 2 16 40 52 66 90
run Y+110 103,107,111,115 2 16 40 52 66 110
run Y+142 101,109,131,139 2 16 40 52 66 142
echo "$(date '+%F %T') pass D end" >> pass_d.log
