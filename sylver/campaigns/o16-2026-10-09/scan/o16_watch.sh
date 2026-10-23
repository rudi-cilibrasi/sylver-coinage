#!/bin/sh
# Finish (and so notify) when the o16 rescan records an answer, or when it ends.
cd "$(dirname "$0")"
while ! grep -q '"answer": [0-9]' o16_scan2.jsonl 2>/dev/null && ! grep -q "o16 rescan done" o16_scan2.log; do sleep 60; done
grep '"answer": [0-9]' o16_scan2.jsonl 2>/dev/null | python3 -c "import json,sys; [print('ANSWER r=%d m=%d' % (r['r'], r['answer'])) for r in map(json.loads, sys.stdin)]"
tail -n 2 o16_scan2.log
