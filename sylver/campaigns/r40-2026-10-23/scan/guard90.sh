#!/bin/bash
# collect.py has no memory guard, and its solve of B66's move 90 (reply 463, Frobenius 581) has grown to 23 GB in an
# hour. Stop that kunz (PID $1) if MemAvailable falls below 15 GB or at the deadline $2 (seconds since the epoch),
# and log it; collect.py then fails, and its log keeps the rows already written.
while kill -0 "$1" 2>/dev/null; do
  avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  if [ "$avail" -lt 15728640 ]; then
    echo "$(date '+%F %T') stopped kunz $1 (B66 move 90): MemAvailable $avail kB, RSS $(ps -o rss= -p "$1") kB" >> guard90.log; kill "$1"; break
  fi
  if [ "$(date +%s)" -ge "$2" ]; then
    echo "$(date '+%F %T') stopped kunz $1 (B66 move 90) at the deadline, RSS $(ps -o rss= -p "$1") kB" >> guard90.log; kill "$1"; break
  fi
  sleep 5
done
