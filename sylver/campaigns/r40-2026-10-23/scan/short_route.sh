#!/bin/bash
# For each candidate R: resolve the even obligations whose child is short (--short-only), then test
# those children whose odd obligations are all N for being P (test_children.sh stops at the first P).
for r in "$@"; do
  echo "$(date '+%F %T') even short-only $r start" >> even_triage.log
  nice -n 10 /usr/bin/python3 even_resolver.py $r --short-only --p-table --ncache-mb 8192 --threads 10 \
      --max-states 100000000 --timeout 300 >> even_triage.log 2>&1
  rc=$?
  echo "$(date '+%F %T') even short-only $r end (exit $rc)" >> even_triage.log
  kids=$(/usr/bin/python3 -c "
import json, sys
rows = {}
for line in open('even_$r.jsonl'):
    x = json.loads(line); rows[x['e']] = x
print(' '.join(str(e) for e, x in sorted(rows.items()) if x['status'] == 'short: needs even'))")
  refuted=$(/usr/bin/python3 -c "
import json
print(any(json.loads(l)['status'] == 'REFUTES r' for l in open('even_$r.jsonl')))")
  if [ "$refuted" = True ] || [ -z "$kids" ]; then continue; fi
  ./test_children.sh $r $kids
done
