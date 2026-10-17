#!/bin/sh
# Independent rerun of the hunt's witness {16,38,72,116}+229 (P, kunz_pt -march=native, 10 threads,
# 16 GB cache, 81,370,519 P entries): kunz_solver from main 0717a1d built at -O2 for any x86-64,
# 2 threads, split depth 4, a 4 GB cache. Niced, 16 GB of address space at most, 8 hours at most.
cd "$(dirname "$0")"
date '+start %F %T'
nice -n 15 prlimit --as=17179869184 timeout 28800 ./kunz_check --threads 2 --split-depth 4 --stop-at-p \
  --max-states 1200000000 --p-table --ncache-mb 4096 --memo-stats --odd-list 229 16 38 72 116
echo "exit $?"
date '+end %F %T'
