#!/bin/bash
# Once LOG has a line matching PATTERN, stop the process tree rooted at ROOT (deepest first).
root=$1; log=$2; pattern=$3
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 "$root" 2>/dev/null; do
  if grep -q -- "$pattern" "$log"; then
    for p in $(tree "$root"); do kill "$p" 2>/dev/null; done
    echo "$(date '+%F %T') stopped the run after '$pattern'" >> "$log"
    exit 0
  fi
  sleep 5
done
echo "root exited on its own"
