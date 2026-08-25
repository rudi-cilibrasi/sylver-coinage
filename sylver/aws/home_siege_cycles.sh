#!/bin/bash
# Home-siege cycle wrapper: run the compact engine in fixed SIGINT
# checkpoint cycles so no more than one cycle of work is ever at risk,
# mirroring the AWS controller's discipline.  Stops on any terminal
# signal, on repeated crashes, or when the block budget is exhausted.
#
# usage: home_siege_cycles.sh ENGINE_BINARY WORKDIR BLOCK_SECONDS CYCLE_SECONDS
set -u
ENGINE_BIN=$1
WORKDIR=$2
BLOCK_SECONDS=$3
CYCLE_SECONDS=$4
START=$(date +%s)
CRASHES=0
LOG="$WORKDIR/run.log"

while true; do
  NOW=$(date +%s); LEFT=$((BLOCK_SECONDS - (NOW - START)))
  [ "$LEFT" -le 900 ] && { echo "BLOCK-BUDGET reached" >> "$LOG"; exit 0; }
  CYCLE=$((LEFT < CYCLE_SECONDS ? LEFT - 600 : CYCLE_SECONDS))
  timeout --preserve-status --signal=INT --kill-after=600 "$CYCLE" \
    "$ENGINE_BIN" "$WORKDIR/periodicity_x.cache" 409 \
    --base-record sylver/move26_data/full_82.txt \
    --base-record sylver/move26_data/x_sortie.txt \
    --exact-threads 8 --batch-pending 10000 --memory-report \
    16 26 82 88 >> "$LOG" 2>&1
  RC=$?
  grep -q "P-HIT\|PERIOD " "$LOG" && { echo "TERMINAL-SIGNAL" >> "$LOG"; exit 0; }
  if [ "$RC" -eq 0 ]; then echo "ROW-COMPLete rc=0" >> "$LOG"; exit 0; fi
  if [ "$RC" -ne 75 ] && [ "$RC" -ne 130 ]; then
    CRASHES=$((CRASHES + 1))
    echo "CYCLE-CRASH rc=$RC count=$CRASHES" >> "$LOG"
    [ "$CRASHES" -ge 3 ] && { echo "CRASH-LOOP stop" >> "$LOG"; exit 1; }
    sleep 60
  else
    CRASHES=0
    echo "CYCLE-CHECKPOINT rc=$RC $(date -u +%FT%TZ)" >> "$LOG"
  fi
done
