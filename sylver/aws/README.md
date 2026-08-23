# AWS spot campaign infrastructure (row-409 siege, phase 1)

Launched 2026-08-23.  One r7a.16xlarge (64 vCPU / 512 GiB) one-shot spot
instance in us-east-2b (~$1.14/h after us-east-1 capacity evaporated),
resuming the audited row-409 checkpoint with `--exact-threads` batch
parallel fallbacks.  Budget: ~$60 phase 1 of a ~$100 total authorization.

`spot_userdata.sh` is the complete in-instance controller.  Safety
layers, in order of arming:

1. **Dead-man timer** — `shutdown -h +3480` (58 h) is the first line
   executed at boot, with `InstanceInitiatedShutdownBehavior=terminate`,
   so a wedged box always dies.
2. **Checkpoint cycles** — the engine runs in 4-hour `timeout --signal
   INT` cycles; each SIGINT saves the atomic rowstate, then cache and
   rowstate sync to S3 (`s3://sylver-conway-011608065382`).
3. **Adaptive memory guard** — at 450 GB RSS the guard SIGINTs the
   engine and the cycle loop halves the worker width (32 → 16 → 12,
   below 12 → terminate).  Exit 75 and 130 both mean "checkpoint
   saved"; three other exits in a row → terminate (no crash-loop burn).
4. **Spot-interruption watcher** — polls IMDSv2 `instance-action`;
   on the 2-minute warning SIGINTs the engine and rescues the cache.
5. **Off-box watchdog** — a monitor on the home machine force-
   terminates past 59 h or at an estimated $70 spend, with API-fault
   tolerance.

Endgame markers uploaded to `status/`: `SUCCESS-PHIT` (X is N — 88
answers move 26), `SUCCESS-PERIOD` (odd tail closed — X is P given the
banked even flank), `DONE-limit` (row 409 completed, no P — the odd
frontier advances past 409), `DONE-timebudget`, `STOPPED-*`,
`FAILED-*`.

Lessons already paid for (~$1 total):
- Ubuntu 24.04 has no `awscli` apt package; a combined
  `apt-get install g++ awscli` fails as a unit, leaving neither — the
  first instance self-terminated blind in 4 minutes.  Install AWS CLI
  v2 from Amazon's zip and upload a `BOOT-OK` marker early.
- 48 solver threads × multi-GB memos exceeded 460 GB during the first
  192,000-position batch; width is now adaptive (start 32, halve on
  guard fire) and the batch cap is 24,000 pending (96,000 hard cap).
- Spot capacity moves: us-east-1f advertised $0.62 with no capacity at
  all; r6a vanished from every us-east-1 AZ within the hour and r6i's
  floor tripled.  Chase the *fulfillable* price, not the lowest listed.
