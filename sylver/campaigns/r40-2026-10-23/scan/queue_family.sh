#!/bin/bash
# Once the test of {16,40,86}+36 ends, stop short_route2.sh (PID $1, before it resumes 86's pass), test
# {16,36,40,50} and {16,36,40,70} (family36.sh), then resume 86's pass (short_route2.sh 86).
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
until grep -qF 'test child {16,40,86}+36 end' test_children.log; do
  kill -0 "$1" 2>/dev/null || exit 1
  sleep 5
done
for p in $(tree "$1"); do kill "$p" 2>/dev/null; done
echo "$(date '+%F %T') stopped the route after 'test child {16,40,86}+36 end', to test {16,36,40,50} and {16,36,40,70} first" >> even_triage.log
./family36.sh 50 70
./short_route2.sh 86
