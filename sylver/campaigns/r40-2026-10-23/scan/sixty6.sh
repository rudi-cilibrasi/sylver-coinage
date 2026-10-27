#!/bin/bash
# 66's even side. Pass C found 66's last three odd obligations N (deep_66.out), so every odd obligation of
# {16,40,66} leads to N by search. This waits for pass C's 74 to end (pass_c.log), stops pass C there (pass_c.sh,
# PID $1, and its kunz_pt for 86) so that one solver runs at a time, then runs even_resolver.py on 66's 33 even
# obligations whose children are long (the 23 short ones are in even_66.jsonl from October 23-24): a reply to
# a known P-position, or the least odd w <= 401 whose finite child is P (kunz_pt --p-table, 400M P-positions and
# 20 minutes a batch). Stopped if MemAvailable falls below 15 GB.
cd "$(dirname "$0")" || exit 1
C_SH=$1
echo "$(date '+%F %T') waiting for pass C's 74 to end" >> sixty6.log
while kill -0 "$C_SH" 2>/dev/null && ! grep -q -F '74 end' pass_c.log; do sleep 5; done
if kill -0 "$C_SH" 2>/dev/null; then
  kill -STOP "$C_SH"
  kids=$(ps -o pid= --ppid "$C_SH")
  kill $kids 2>/dev/null
  kill -TERM "$C_SH"; kill -CONT "$C_SH"
  echo "$(date '+%F %T') stopped pass C after: $(grep -F '74 end' pass_c.log) (killed pass_c.sh $C_SH and $kids)" >> sixty6.log
  echo "$(date '+%F %T') stopped here by sixty6.sh, for 66's even side" >> pass_c.log
fi
echo "$(date '+%F %T') even_resolver.py 66 start" >> sixty6.log
nice -n 10 /usr/bin/python3 even_resolver.py 66 --p-table --ncache-mb 8192 --threads 10 --short-first \
    --max-states 400000000 --timeout 1200 >> sixty6.log 2>&1 &
pid=$!
tree() { local p; for p in $(ps -o pid= --ppid "$1"); do tree "$p"; done; echo "$1"; }
while kill -0 $pid 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopping: MemAvailable $avail kB is below 15 GB" >> sixty6.log
    for p in $(tree $pid); do kill $p 2>/dev/null; done
    break
  fi
  sleep 10
done
wait $pid
rc=$?
echo "$(date '+%F %T') exit $rc" >> sixty6.log
