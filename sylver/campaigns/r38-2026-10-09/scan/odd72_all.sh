#!/bin/sh
# All 25 odd obligations of {16,38,72} in one sweep, to record a winning move for each (October 18):
# odd_filter.jsonl kept only a count for the first 22, and odd72.* has the last three. kunz is the
# scan's build of sylver/kunz_solver.cpp at 0668ae4. Niced, 30 GB of address space and an hour at most.
cd "$(dirname "$0")"
nice -n 10 prlimit --as=32212254720 timeout 3600 ./kunz --threads 8 --stop-at-p --max-states 900000000 \
  --odd-list 3,5,7,9,11,13,15,17,21,23,25,29,31,33,37,39,41,45,47,49,53,61,69,77,85 16 38 72
