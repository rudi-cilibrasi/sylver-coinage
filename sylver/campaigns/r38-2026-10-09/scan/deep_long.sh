#!/bin/sh
# Deeper odd-witness sweeps of the long candidates the map searched with a 150M cap per batch:
# each resumes after the map's first replies (--done-count) and retries the ones it skipped (--also).
cd "$(dirname "$0")"
echo "$(date +%T) start 52" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 40 --also 69,77,87,89 --threads 4 --max-states 700000000 --max-skips 8 16 38 52 >> deep_long.out 2>&1
echo "$(date +%T) end 52 rc=$?" >> deep_long.log
echo "$(date +%T) start 62" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 34 --also 59,69,71,77 --threads 4 --max-states 700000000 --max-skips 8 16 38 62 >> deep_long.out 2>&1
echo "$(date +%T) end 62 rc=$?" >> deep_long.log
echo "$(date +%T) start 66" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 39 --also 49,75,81,87 --threads 4 --max-states 700000000 --max-skips 8 16 38 66 >> deep_long.out 2>&1
echo "$(date +%T) end 66 rc=$?" >> deep_long.log
echo "$(date +%T) start 68" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 32 --also 63,79,65,69 --threads 4 --max-states 700000000 --max-skips 8 16 38 68 >> deep_long.out 2>&1
echo "$(date +%T) end 68 rc=$?" >> deep_long.log
echo "$(date +%T) start 74" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 29 --also 71,79,53,61 --threads 4 --max-states 700000000 --max-skips 8 16 38 74 >> deep_long.out 2>&1
echo "$(date +%T) end 74 rc=$?" >> deep_long.log
echo "$(date +%T) start 82" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 29 --also 27,41,85,59 --threads 4 --max-states 700000000 --max-skips 8 16 38 82 >> deep_long.out 2>&1
echo "$(date +%T) end 82 rc=$?" >> deep_long.log
echo "$(date +%T) start 84" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 28 --also 49,71,79,59 --threads 4 --max-states 700000000 --max-skips 8 16 38 84 >> deep_long.out 2>&1
echo "$(date +%T) end 84 rc=$?" >> deep_long.log
echo "$(date +%T) start 90" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 28 --also 63,43,61,71 --threads 4 --max-states 700000000 --max-skips 8 16 38 90 >> deep_long.out 2>&1
echo "$(date +%T) end 90 rc=$?" >> deep_long.log
echo "$(date +%T) start 106" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 63,49,71,51 --threads 4 --max-states 700000000 --max-skips 8 16 38 106 >> deep_long.out 2>&1
echo "$(date +%T) end 106 rc=$?" >> deep_long.log
echo "$(date +%T) start 110" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 28 --also 43,49,51,59 --threads 4 --max-states 700000000 --max-skips 8 16 38 110 >> deep_long.out 2>&1
echo "$(date +%T) end 110 rc=$?" >> deep_long.log
echo "$(date +%T) start 116" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 49,71,79,51 --threads 4 --max-states 700000000 --max-skips 8 16 38 116 >> deep_long.out 2>&1
echo "$(date +%T) end 116 rc=$?" >> deep_long.log
echo "$(date +%T) start 122" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 63,49,71,79 --threads 4 --max-states 700000000 --max-skips 8 16 38 122 >> deep_long.out 2>&1
echo "$(date +%T) end 122 rc=$?" >> deep_long.log
echo "$(date +%T) start 126" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 27 --also 35,43,51,85 --threads 4 --max-states 700000000 --max-skips 8 16 38 126 >> deep_long.out 2>&1
echo "$(date +%T) end 126 rc=$?" >> deep_long.log
echo "$(date +%T) start 132" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 49,63,51,71 --threads 4 --max-states 700000000 --max-skips 8 16 38 132 >> deep_long.out 2>&1
echo "$(date +%T) end 132 rc=$?" >> deep_long.log
echo "$(date +%T) start 138" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 63,49,71,43 --threads 4 --max-states 700000000 --max-skips 8 16 38 138 >> deep_long.out 2>&1
echo "$(date +%T) end 138 rc=$?" >> deep_long.log
echo "$(date +%T) start 142" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 26 --also 35,43,63,85 --threads 4 --max-states 700000000 --max-skips 8 16 38 142 >> deep_long.out 2>&1
echo "$(date +%T) end 142 rc=$?" >> deep_long.log
echo "$(date +%T) start 148" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 43,49,51,59 --threads 4 --max-states 700000000 --max-skips 8 16 38 148 >> deep_long.out 2>&1
echo "$(date +%T) end 148 rc=$?" >> deep_long.log
echo "$(date +%T) start 154" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 63,49,71,43 --threads 4 --max-states 700000000 --max-skips 8 16 38 154 >> deep_long.out 2>&1
echo "$(date +%T) end 154 rc=$?" >> deep_long.log
echo "$(date +%T) start 158" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 26 --also 41,63,43,85 --threads 4 --max-states 700000000 --max-skips 8 16 38 158 >> deep_long.out 2>&1
echo "$(date +%T) end 158 rc=$?" >> deep_long.log
echo "$(date +%T) start 164" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 35,43,49,51 --threads 4 --max-states 700000000 --max-skips 8 16 38 164 >> deep_long.out 2>&1
echo "$(date +%T) end 164 rc=$?" >> deep_long.log
echo "$(date +%T) start 170" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 45,49,43,79 --threads 4 --max-states 700000000 --max-skips 8 16 38 170 >> deep_long.out 2>&1
echo "$(date +%T) end 170 rc=$?" >> deep_long.log
echo "$(date +%T) start 180" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 41,43,63,49 --threads 4 --max-states 700000000 --max-skips 8 16 38 180 >> deep_long.out 2>&1
echo "$(date +%T) end 180 rc=$?" >> deep_long.log
echo "$(date +%T) start 186" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 21 --also 45,49,63,71 --threads 4 --max-states 700000000 --max-skips 8 16 38 186 >> deep_long.out 2>&1
echo "$(date +%T) end 186 rc=$?" >> deep_long.log
echo "$(date +%T) start 196" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 26 --also 41,63,43,85 --threads 4 --max-states 700000000 --max-skips 8 16 38 196 >> deep_long.out 2>&1
echo "$(date +%T) end 196 rc=$?" >> deep_long.log
echo "$(date +%T) start 202" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 41,49,63,71 --threads 4 --max-states 700000000 --max-skips 8 16 38 202 >> deep_long.out 2>&1
echo "$(date +%T) end 202 rc=$?" >> deep_long.log
echo "$(date +%T) start 212" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 25 --also 41,63,49,71 --threads 4 --max-states 700000000 --max-skips 8 16 38 212 >> deep_long.out 2>&1
echo "$(date +%T) end 212 rc=$?" >> deep_long.log
echo "$(date +%T) start 218" >> deep_long.log
timeout 3600 nice -n 10 python3 deep_witness.py --done-count 24 --also 41,63,49,51 --threads 4 --max-states 700000000 --max-skips 8 16 38 218 >> deep_long.out 2>&1
echo "$(date +%T) end 218 rc=$?" >> deep_long.log
echo "deep long done" >> deep_long.log
