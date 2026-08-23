#!/bin/bash
# Sylver row-409 spot campaign — phase 1 (58h hard cap).
# Layers: (1) dead-man shutdown+terminate at 58h armed FIRST,
# (2) engine SIGINT checkpoint cycles with S3 sync, (3) memory guard,
# (4) spot-interruption handler.  Local watchdog is layer 5, off-box.
set -x
exec > /var/log/sylver-campaign.log 2>&1

# Layer 1: dead-man timer before anything else can fail.
shutdown -h +3480

BUCKET=s3://sylver-conway-011608065382
START=$(date +%s)
DEADLINE=$((START + 205200))   # 57h; shutdown timer is 58h
mkdir -p /data && cd /data

for try in 1 2 3; do apt-get update -y && break; sleep 20; done
DEBIAN_FRONTEND=noninteractive apt-get install -y g++ unzip curl
# Ubuntu 24.04 has no awscli apt package; use Amazon's v2 installer.
curl -s https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o /tmp/awscli.zip
unzip -q /tmp/awscli.zip -d /tmp && /tmp/aws/install
export PATH=/usr/local/bin:$PATH
TOK=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOK" http://169.254.169.254/latest/meta-data/instance-id)
echo "BOOT-OK $(date -u +%FT%TZ) $IID g++=$(command -v g++) aws=$(command -v aws)" > /tmp/boot
aws s3 cp /tmp/boot "$BUCKET/status/BOOT-OK" || true

finish () {  # $1 = marker name
  aws s3 cp /data/periodicity_x.cache "$BUCKET/output/periodicity_x.cache" || true
  aws s3 cp /data/periodicity_x.cache.rowstate "$BUCKET/output/periodicity_x.cache.rowstate" || true
  aws s3 cp /var/log/sylver-campaign.log "$BUCKET/output/campaign.log" || true
  aws s3 cp /data/run.log "$BUCKET/output/run.log" || true
  echo "$1 $(date -u +%FT%TZ) elapsed=$((($(date +%s)-START)/60))min" > /data/marker
  aws s3 cp /data/marker "$BUCKET/status/$1" || true
  aws ec2 terminate-instances --region us-east-1 --instance-ids "$IID" || shutdown -h now
  exit 0
}

status () {
  echo "$1 $(date -u +%FT%TZ) elapsed=$((($(date +%s)-START)/60))min $(tail -c 300 /data/run.log 2>/dev/null | tr '\n' ' ')" > /data/st
  aws s3 cp /data/st "$BUCKET/status/latest.txt" || true
}

# Fetch artifacts; prefer newer output/ state from a prior cycle.
for f in periodicity_engine.cpp full_82.txt x_sortie.txt; do
  aws s3 cp "$BUCKET/input/$f" "/data/$f" || finish FAILED-fetch
done
for f in periodicity_x.cache periodicity_x.cache.rowstate; do
  aws s3 cp "$BUCKET/output/$f" "/data/$f" || \
  aws s3 cp "$BUCKET/input/$f" "/data/$f" || finish FAILED-fetch
done

g++ -std=c++20 -O3 -Wall -Wextra -pedantic -pthread periodicity_engine.cpp -o engine || finish FAILED-compile

# Shakedown 1: {8,10,22} differential control with threads.
timeout 300 ./engine /data/ctl.cache 201 --exact-threads 4 8 10 22 > /data/ctl.log 2>&1
grep -q "PERIOD start=49 length=8 shapes=50" /data/ctl.log || finish FAILED-control

# Shakedown 2: resume the real rowstate, advance one evaluation, save.
cp periodicity_x.cache shk.cache && cp periodicity_x.cache.rowstate shk.cache.rowstate
timeout 1800 ./engine /data/shk.cache 409 --base-record full_82.txt --base-record x_sortie.txt \
  --exact-threads 48 --batch-pending 48000 --stop-after-evaluations 22641269 16 26 82 88 > /data/shk.log 2>&1
grep -q "ROW-CHECKPOINT saved" /data/shk.log || finish FAILED-shakedown
rm -f shk.cache shk.cache.rowstate
status SHAKEDOWN-OK

# Layer 3: memory guard (450 GB RSS) — flags GUARD so the cycle loop
# halves the worker width and continues rather than terminating.
( while true; do
    R=$(ps -o rss= -C engine | sort -n | tail -1)
    [ -n "$R" ] && [ "$R" -ge 471859200 ] && touch /data/GUARD && pkill -INT -x engine && sleep 300
    sleep 30
  done ) &
( while true; do
    T2=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
    A=$(curl -s -o /dev/null -w '%{http_code}' -H "X-aws-ec2-metadata-token: $T2" http://169.254.169.254/latest/meta-data/spot/instance-action)
    [ "$A" = "200" ] && pkill -INT -x engine && touch /data/STOP && \
      aws s3 cp /data/periodicity_x.cache "$BUCKET/output/periodicity_x.cache" && break
    sleep 5
  done ) &

# Layer 2: 4-hour checkpoint cycles with adaptive worker width.
CRASHES=0
THREADS=32
while true; do
  [ -f /data/STOP ] && finish STOPPED-interrupt
  if [ -f /data/GUARD ]; then
    THREADS=$((THREADS / 2)); rm -f /data/GUARD
    [ "$THREADS" -lt 12 ] && finish STOPPED-lowmem
    status "GUARD-halved-to-$THREADS"
  fi
  NOW=$(date +%s); LEFT=$((DEADLINE - NOW))
  [ "$LEFT" -le 600 ] && finish DONE-timebudget
  CYCLE=$((LEFT < 14400 ? LEFT - 300 : 14400))
  timeout --preserve-status --signal=INT --kill-after=600 "$CYCLE" \
    ./engine /data/periodicity_x.cache 409 \
    --base-record full_82.txt --base-record x_sortie.txt \
    --exact-threads "$THREADS" --batch-pending 24000 16 26 82 88 >> /data/run.log 2>&1
  RC=$?
  grep -q "P-HIT" /data/run.log && finish SUCCESS-PHIT
  grep -q "PERIOD " /data/run.log && finish SUCCESS-PERIOD
  if [ "$RC" -eq 0 ]; then finish DONE-limit; fi
  # 75 = timed checkpoint, 130 = guard/interrupt SIGINT; both saved cleanly.
  if [ "$RC" -ne 75 ] && [ "$RC" -ne 130 ]; then
     CRASHES=$((CRASHES+1)); status "ENGINE-RC-$RC-crash$CRASHES"; sleep 30
     grep -q "checkpoint error\|exceeds\|conflicts" /data/run.log && finish FAILED-engine
     [ "$CRASHES" -ge 3 ] && finish FAILED-crashloop
  else CRASHES=0; fi
  aws s3 cp /data/periodicity_x.cache "$BUCKET/output/periodicity_x.cache" || true
  aws s3 cp /data/periodicity_x.cache.rowstate "$BUCKET/output/periodicity_x.cache.rowstate" || true
  status "CYCLE-OK-threads$THREADS"
done
