#!/bin/bash
# Stop the screen (python pid $1) at a candidate boundary: once screen.log has an odd-stage line
# for a candidate >= $2, kill the solver the screen just started, then the screen itself.
py=$1; limit=$2
while kill -0 "$py" 2>/dev/null; do
  if awk -v L="$limit" '$2=="odd" && $1+0>=L {f=1} END {exit !f}' screen.log; then
    for c in $(ps -o pid= --ppid "$py"); do kill "$c"; done
    kill "$py"; sleep 2
    echo "$(date '+%F %T') stopped pass A after candidate >= $limit (resume with --amin $((limit+4)))" >> screen.log
    exit 0
  fi
  sleep 20
done
echo "screen exited on its own"
