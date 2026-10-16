#!/bin/sh
# Memory guard for the hunt: when available memory falls below 6 GB, stop the running hunt's
# solve (kunz_pt children of the PID in hunt.pid), freeing its cache at once. The hunt logs that
# reply as interrupted and tries it again later, starting solves only with enough memory free.
# Ends when no hunt has run for ten minutes.
cd "$(dirname "$0")"
idle=0
while [ $idle -lt 30 ]; do
  hunt=$(cat hunt.pid 2>/dev/null)
  if [ -n "$hunt" ] && kill -0 "$hunt" 2>/dev/null; then
    idle=0
    avail=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
    if [ "$avail" -lt 6291456 ]; then
      for p in $(ps -o pid= --ppid "$hunt"); do
        if [ "$(cat /proc/$p/comm 2>/dev/null)" = "kunz_pt" ]; then
          kill -TERM "$p" && echo "$(date +%T) memguard: MemAvailable $((avail / 1024)) MB < 6 GB, stopped solve $p" >> hunt.log
        fi
      done
      sleep 120
    fi
  else
    idle=$((idle + 1))
  fi
  sleep 20
done
