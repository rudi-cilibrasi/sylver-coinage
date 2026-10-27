#!/bin/bash
# Pass I: pass H's leftovers with more time. Pass H (PID $1) gave 86's and 82's open odd obligations 4 hours each;
# 86 stopped at the limit with 8 of 16 classified (all N), 40 minutes into 105, and 82 with 14 of 15 (all N; 135
# open). This waits for pass H to end, then reruns each answer's unclassified obligations (read from deep_82.out and
# deep_86.out) with kunz_pt --p-table --stop-at-p, the same 800M cap and 8 hours: 82 first, whose one row decides
# whether it is odd-complete. An answer whose pass H run already has a P row is refuted and skipped.
# Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') waiting for pass H ($1) to end" >> pass_i.log
while kill -0 "$1" 2>/dev/null; do sleep 10; done

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
  echo "$(date '+%F %T') $tag start: {$*} + $list (${hours} h)" >> pass_i.log
  nice -n 10 $cmd > "deep_$tag.out" 2>> "deep_$tag.err" &
  local pid=$!
  memguard $pid "$hours" "deep_$tag.err"
  wait $pid
  local rc=$?
  echo "$(date '+%F %T') exit $rc" >> "deep_$tag.err"
  local n p
  n=$(grep -c '^move=' "deep_$tag.out")
  p=$(awk '/^move=/ && $2 == "P" {print $1}' "deep_$tag.out")
  echo "$(date '+%F %T') $tag end: exit $rc, $n of $(tr ',' '\n' <<< "$list" | wc -l) classified${p:+, P: $p}" >> pass_i.log
}

leftover() {   # pass H's odd list, its output: the moves with no row, comma-separated
  awk -v list="$1" '/^move=/ {split($1, a, "="); done[a[2]] = 1}
    END {n = split(list, m, ","); s = ""; for (i = 1; i <= n; i++) if (!(m[i] in done)) s = s (s ? "," : "") m[i]; print s}' "$2"
}

for answer in 82 86; do
  if [ "$answer" = 86 ]; then list=73,77,81,85,89,93,97,101,105,109,113,117,121,125,133,141
  else list=71,75,79,83,87,91,95,99,103,107,111,115,119,127,135; fi
  if awk '/^move=/ && $2 == "P" {found = 1} END {exit !found}' "deep_$answer.out"; then
    echo "$(date '+%F %T') $answer skipped: pass H found a P row" >> pass_i.log; continue
  fi
  rest=$(leftover "$list" "deep_$answer.out")
  if [ -z "$rest" ]; then echo "$(date '+%F %T') $answer skipped: pass H classified all" >> pass_i.log; continue; fi
  run "${answer}x" "$rest" 8 16 40 "$answer"
done
echo "$(date '+%F %T') pass I end" >> pass_i.log
