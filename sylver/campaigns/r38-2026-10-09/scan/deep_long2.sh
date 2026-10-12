#!/bin/sh
# Second deeper pass over the open long candidates of {16,38}: two hours each at the first pass's
# 700M-state cap, resuming after the map's replies (--done-count, --also) and leaving out every reply
# the first deeper pass classified or gave up on (--exclude), so the time goes to replies never tried.
cd "$(dirname "$0")"
echo "$(date +%T) start 42" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 106 --also 205,213,215,221 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 42 >> deep_long2.out 2>&1
echo "$(date +%T) end 42 rc=$?" >> deep_long2.log
echo "$(date +%T) start 46" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 68 --also 129,141,143,145 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 46 >> deep_long2.out 2>&1
echo "$(date +%T) end 46 rc=$?" >> deep_long2.log
echo "$(date +%T) start 62" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 34 --also 59,69,71,77 --exclude 59,69,71,73,75,77,79,81,83,85,87,89,91,93,95,97,99,101,103,105,107,109,111,113,115,117,119 --threads 4 --max-states 700000000 --max-skips 12 16 38 62 >> deep_long2.out 2>&1
echo "$(date +%T) end 62 rc=$?" >> deep_long2.log
echo "$(date +%T) start 66" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 39 --also 49,75,81,87 --exclude 49,75,81,83,85,87,89,91,93,95,97,99,101,103,105,107 --threads 4 --max-states 700000000 --max-skips 12 16 38 66 >> deep_long2.out 2>&1
echo "$(date +%T) end 66 rc=$?" >> deep_long2.log
echo "$(date +%T) start 68" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 32 --also 63,79,65,69 --exclude 63,65,67,69,73,75,77,79,81,83,85,87,89,91,93,95,97,99,101,103,105,107,109,111 --threads 4 --max-states 700000000 --max-skips 12 16 38 68 >> deep_long2.out 2>&1
echo "$(date +%T) end 68 rc=$?" >> deep_long2.log
echo "$(date +%T) start 74" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 29 --also 71,79,53,61 --exclude 53,57,59,61,65,67,69,71,73,75,77,79,81,83,85,87,89,91,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 74 >> deep_long2.out 2>&1
echo "$(date +%T) end 74 rc=$?" >> deep_long2.log
echo "$(date +%T) start 82" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 29 --also 27,41,85,59 --exclude 27,41,51,57,59,63,65,67,71,73,75,79,81,83,85,87,89,91,93,95,97,99 --threads 4 --max-states 700000000 --max-skips 12 16 38 82 >> deep_long2.out 2>&1
echo "$(date +%T) end 82 rc=$?" >> deep_long2.log
echo "$(date +%T) start 84" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 28 --also 49,71,79,59 --exclude 49,51,53,57,59,61,65,67,69,71,79,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 84 >> deep_long2.out 2>&1
echo "$(date +%T) end 84 rc=$?" >> deep_long2.log
echo "$(date +%T) start 90" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 28 --also 63,43,61,71 --exclude 43,57,59,61,63,71 --threads 4 --max-states 700000000 --max-skips 12 16 38 90 >> deep_long2.out 2>&1
echo "$(date +%T) end 90 rc=$?" >> deep_long2.log
echo "$(date +%T) start 106" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 63,49,71,51 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 106 >> deep_long2.out 2>&1
echo "$(date +%T) end 106 rc=$?" >> deep_long2.log
echo "$(date +%T) start 116" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 49,71,79,51 --exclude 43,45,49,51,53,57,59,61,65,67,69,71,79,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 116 >> deep_long2.out 2>&1
echo "$(date +%T) end 116 rc=$?" >> deep_long2.log
echo "$(date +%T) start 122" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 63,49,71,79 --exclude 49,63,71 --threads 4 --max-states 700000000 --max-skips 12 16 38 122 >> deep_long2.out 2>&1
echo "$(date +%T) end 122 rc=$?" >> deep_long2.log
echo "$(date +%T) start 126" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 27 --also 35,43,51,85 --exclude 35,43,49,51,85 --threads 4 --max-states 700000000 --max-skips 12 16 38 126 >> deep_long2.out 2>&1
echo "$(date +%T) end 126 rc=$?" >> deep_long2.log
echo "$(date +%T) start 132" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 49,63,51,71 --exclude 45,49,51,63,71 --threads 4 --max-states 700000000 --max-skips 12 16 38 132 >> deep_long2.out 2>&1
echo "$(date +%T) end 132 rc=$?" >> deep_long2.log
echo "$(date +%T) start 138" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 63,49,71,43 --exclude 49,63,71 --threads 4 --max-states 700000000 --max-skips 12 16 38 138 >> deep_long2.out 2>&1
echo "$(date +%T) end 138 rc=$?" >> deep_long2.log
echo "$(date +%T) start 142" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 26 --also 35,43,63,85 --exclude 35,43,49,51,57,59,63,77,85,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 142 >> deep_long2.out 2>&1
echo "$(date +%T) end 142 rc=$?" >> deep_long2.log
echo "$(date +%T) start 148" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 43,49,51,59 --exclude 43,49,51,53,55,57,59,61,63,65,67,69,71,73,75,77,79,81,83 --threads 4 --max-states 700000000 --max-skips 12 16 38 148 >> deep_long2.out 2>&1
echo "$(date +%T) end 148 rc=$?" >> deep_long2.log
echo "$(date +%T) start 154" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 63,49,71,43 --exclude 27,35,43,49,51,53,57,59,61,63,65,67,69,71,79,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 154 >> deep_long2.out 2>&1
echo "$(date +%T) end 154 rc=$?" >> deep_long2.log
echo "$(date +%T) start 158" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 26 --also 41,63,43,85 --exclude 35,41,43,49,51,63,71,77,85,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 158 >> deep_long2.out 2>&1
echo "$(date +%T) end 158 rc=$?" >> deep_long2.log
echo "$(date +%T) start 164" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 35,43,49,51 --exclude 35,43,49,51,57,59,61,63,65,67,69,71,73,77,85 --threads 4 --max-states 700000000 --max-skips 12 16 38 164 >> deep_long2.out 2>&1
echo "$(date +%T) end 164 rc=$?" >> deep_long2.log
echo "$(date +%T) start 170" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 45,49,43,79 --exclude 35,43,45,49,51,53,57,59,61,65,67,69,73,75,77,79,81,83,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 170 >> deep_long2.out 2>&1
echo "$(date +%T) end 170 rc=$?" >> deep_long2.log
echo "$(date +%T) start 180" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 41,43,63,49 --exclude 41,43,49,51,57,59,63,65,67,69,71,73,75,77,85,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 180 >> deep_long2.out 2>&1
echo "$(date +%T) end 180 rc=$?" >> deep_long2.log
echo "$(date +%T) start 186" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 21 --also 45,49,63,71 --exclude 19,27,35,43,45,49,51,53,57,59,61,63,65,67,69,71,79,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 186 >> deep_long2.out 2>&1
echo "$(date +%T) end 186 rc=$?" >> deep_long2.log
echo "$(date +%T) start 196" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 26 --also 41,63,43,85 --exclude 35,41,43,49,51,63,71,77,85,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 196 >> deep_long2.out 2>&1
echo "$(date +%T) end 196 rc=$?" >> deep_long2.log
echo "$(date +%T) start 202" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 24 --also 41,49,63,71 --exclude 41,43,49,51,53,57,59,61,63,65,67,69,71,79,87 --threads 4 --max-states 700000000 --max-skips 12 16 38 202 >> deep_long2.out 2>&1
echo "$(date +%T) end 202 rc=$?" >> deep_long2.log
echo "$(date +%T) start 212" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 25 --also 41,63,49,71 --exclude 35,41,43,49,51,63,69,71,77,85,93 --threads 4 --max-states 700000000 --max-skips 12 16 38 212 >> deep_long2.out 2>&1
echo "$(date +%T) end 212 rc=$?" >> deep_long2.log
echo "$(date +%T) start 234" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 38 --also 71,75,85,83 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 234 >> deep_long2.out 2>&1
echo "$(date +%T) end 234 rc=$?" >> deep_long2.log
echo "$(date +%T) start 250" >> deep_long2.log
timeout 7200 nice -n 10 python3 deep_witness2.py --done-count 35 --also 71,79,85,93 --exclude 0 --threads 4 --max-states 700000000 --max-skips 12 16 38 250 >> deep_long2.out 2>&1
echo "$(date +%T) end 250 rc=$?" >> deep_long2.log
echo "deep long 2 done" >> deep_long2.log
