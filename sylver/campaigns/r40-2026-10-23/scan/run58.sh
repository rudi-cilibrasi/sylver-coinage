#!/bin/bash
# 58's even obligations, short children first (kunz_pt, 100M P-positions, 5 minutes a batch).
echo "$(date '+%F %T') even short-first 58 start" >> even_triage.log
nice -n 10 /usr/bin/python3 even_resolver.py 58 --short-first --p-table --ncache-mb 8192 --threads 10 \
    --max-states 100000000 --timeout 300 >> even_triage.log 2>&1
rc=$?
echo "$(date '+%F %T') even short-first 58 end (exit $rc)" >> even_triage.log
