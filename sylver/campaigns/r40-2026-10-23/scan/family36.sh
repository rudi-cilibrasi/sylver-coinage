#!/bin/bash
# B58={16,36,40,58} and B78={16,36,40,78} are P (search). Are {16,36,40,50} and {16,36,40,70}? Their odd
# obligations are all N (the 'short: needs even' rows of resolve_16-36-40-66.jsonl and resolve_16-36-40-86.jsonl),
# and the children 36 of 66 and 86 reach them ({16,36,40,66}+50, {16,36,40,86}+50 and +70), so they decide
# whether those children can be P. Resolve their even obligations, as test_children.sh does.
for x in "$@"; do
  echo "$(date '+%F %T') test {16,36,40,$x} start" >> test_children.log
  nice -n 10 /usr/bin/python3 even_resolver.py --position 16 36 40 $x --short-first --p-table --ncache-mb 8192 \
      --threads 10 --max-states 100000000 --timeout 300 >> test_children.log 2>&1
  rc=$?
  echo "$(date '+%F %T') test {16,36,40,$x} end (exit $rc)" >> test_children.log
done
