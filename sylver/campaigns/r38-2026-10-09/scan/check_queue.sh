#!/bin/sh
# Run the witness reruns one at a time: 68+257 after 100+245 has finished.
cd "$(dirname "$0")"
until grep -q '^end ' check_100_245.out 2>/dev/null; do sleep 60; done
./check_68_257.sh > check_68_257.out 2>&1
