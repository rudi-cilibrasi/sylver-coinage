# Compact periodicity-engine representation and home-siege resume

Date: 2026-08-24
Status: approved design

## Context

The row-409 campaign measured its own limits: the dependency closure of
`X={16,26,82,88}`'s first new row exceeds 3.15M translated shapes and
12.5M base-region exact positions, unsaturated, at ~13 KB per shape
all-in (`RUN_PERIODICITY_500H.txt`, `RUN_PERIODICITY_AWS.txt`).  The
audited cache holds 267,847 exact outcomes; the resumable 756 MB
version-1 rowstate (324,404 shapes) lives in
`s3://sylver-conway-011608065382/output/`.  Memory, not CPU, binds.

Reading the engine shows where the 13 KB goes:

- `Shape.odd_options`: up to ~120 entries per built shape, each with
  its own heap-allocated offsets vector (~90 B/entry) that is
  deterministically recomputable — ~5–10 KB per built shape.
- `shape_index`: `std::map<std::pair<int,std::vector<int>>,int>` —
  a tree node plus a heap vector per key, ~150 B/shape.
- `ring`/`value_stamp`: two heap vectors per shape (~400 B with
  headers and fragmentation).

## Goal

6–10x memory compaction with **bit-identical outcomes**, a v1→v2
checkpoint migration that preserves the S3 frontier, and a resumed
row-409 siege on the 12-core / 62 GB home box (~15–30M shape headroom).

## Non-goals

- No semantic changes to the recurrence, stamps, reset flags, Brent
  comparison, or sweep order (Approach B items — watermark stamps,
  droppable transition specs — stay in backlog).
- No new compute spend; home box only.
- The letter (`DRAFT_TO_SICHERMAN_BLOK.md`) remains the strategic hedge
  and is unaffected.

## §1 Memory instrumentation (first, and kept)

`--memory-report` prints exact byte accounting by subsystem — shapes
core, transition specs, shape index, ring arena, stamp arena, row memo,
base cache — at every checkpoint save and on demand.  Baseline numbers
are taken on the migrated real frontier before any compaction lands, so
every subsequent change has a measured before/after.

## §2 Layout changes (semantics frozen)

1. **Transition specs.**  `OddOption` stores no offsets.  Layout: a
   tagged 8-byte entry — unregistered: the relative move `r` (int16);
   registered: child sid (int32) + `dmin` (int16).  At registration the
   child's canonical offsets are recomputed transiently through the
   same `canonical()` code path used today, then discarded.
2. **Shape index.**  `std::map` replaced by a flat
   `unordered_map<uint64,int32>` keyed by a 64-bit hash of
   (eid, offsets).  Lookup verifies the candidate's stored offsets
   before trusting it; a genuine 64-bit collision falls back to linear
   probe of an overflow list.  No behavioral dependence on hash quality
   — only speed.
3. **Shape core.**  Offsets pack inline: int16[7] + count byte covers
   every observed shape; wider shapes spill to a shared overflow arena
   (index + length into one big vector).
4. **Ring and stamps.**  Two flat arenas (`vector<signed char>`,
   `vector<int32>`) indexed by `sid * window_slots + slot`, grown
   geometrically.  Same values, same validity rule.

## §3 Checkpoint v2 with v1 migration

- Rowstate format bumps to version 2 (new magic).  The loader accepts
  v1 (the current 505 MB audited local file and the 756 MB S3 frontier)
  and migrates in memory; saving always writes v2.
- The v1 loader's structural validation, checksum, dependency-subset
  check against the exact cache, and the deliberate Brent-candidate
  reset are preserved verbatim in both paths.
- A migration is not a new computation: outcome-bearing state (ring
  values, stamps, reset flags, memo, counters) is carried bit-for-bit.

## §4 Certification gates (all before any siege hour)

1. All existing periodicity differential controls (including
   `{8,10,22}` period start=49 len=8 shapes=50), single- and
   multi-threaded.
2. New v1-vs-v2 equality control: the pre-compaction binary and the
   compacted binary run the same base/limit; period certificate,
   P-HIT sequence, and final cache contents must be identical.
3. Migration round-trip: load a real v1 checkpoint copy, advance one
   evaluation, save v2, reload v2, advance again — counters and
   structures consistent; artifact hashes of the originals unchanged.
4. ASan/UBSan interrupt-resume control on the compacted binary.
5. Warning-clean `-std=c++20 -O2/-O3 -Wall -Wextra -pedantic` builds;
   full sylver test suite; `git diff --check`.

## §5 Home-siege resume

Download and migrate the S3 frontier (record SHA-256 before/after),
then resume with `--exact-threads 10`, `--batch-pending` sized for 12
cores (10,000), and an external 52 GB RSS guard using the proven
SIGINT-checkpoint path.  Blocks follow the repository convention:
fixed budgets, full audit (`RUN_COMPACT_*.txt`), timeboxed review after
each block with the standing pivot rule — two decelerating blocks
without convergence trigger strategy review (the letter, Approach B,
or stop).  Success criteria unchanged and explicit: P-HIT, PERIOD, or
completed row; anything else is a frontier advance, reported as such.

## Testing summary

| Gate | Guards |
| --- | --- |
| `--memory-report` accounting | claims are measured, not estimated |
| v1-vs-v2 equality control | layout cannot change outcomes |
| Migration round-trip | the 756 MB investment survives |
| Periodicity controls (threads on/off) | recurrence untouched |
| ASan/UBSan interrupt-resume | checkpoint safety in the new layout |
| Full suite + clean builds | no regressions anywhere |

## Risks

- Hash collisions in the new index: neutralized by offset verification.
- Migration fidelity: neutralized by round-trip + dependency-subset
  checks and by keeping the v1 originals immutable.
- Strategic: the closure may exceed even compacted memory — the
  drafted letter is the standing hedge; this work multiplies with it.
