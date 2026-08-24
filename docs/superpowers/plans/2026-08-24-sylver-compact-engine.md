# Compact Engine Representation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 6–10x memory compaction of `sylver/periodicity_engine.cpp` with bit-identical outcomes, a v1→v2 checkpoint migration preserving the 756 MB S3 frontier, and a resumed row-409 siege on the home box.

**Architecture:** Four layout replacements at measured hot spots (transition specs, shape index, shape offsets, ring/stamp arenas), semantics frozen. Serialization refactors once to a v2 format whose loader also reads v1 and migrates in memory. Every task keeps the full periodicity suite green; the final gates add a v1-vs-v2 equality control and a migration round-trip on real checkpoints.

**Tech Stack:** C++20, single file `sylver/periodicity_engine.cpp`; tests in `tests/test_sylver_periodicity.py`.

**Spec:** `docs/superpowers/specs/2026-08-24-sylver-compact-engine-design.md`.

## Global Constraints

- Outcomes are sacred: no change to recurrence order, stamp validity rules, reset flags, Brent comparison, or P-HIT semantics. The v1-vs-v2 equality control enforces this.
- The pre-compaction binary is retained (built from git HEAD~) as the differential reference.
- Every task: warning-clean `-O2 -Wall -Wextra -pedantic` build + `python -m unittest tests.test_sylver_periodicity` green + commit.
- The 505 MB local v1 rowstate and the 756 MB S3 v1 rowstate are immutable inputs; migration writes new files.

## Task 1: `--memory-report` instrumentation

Add exact byte accounting per subsystem, printed at every checkpoint save and at `LIMIT-REACHED`/`PERIOD`: shapes core (struct + offsets heap), transition specs (odd_options + even_children), shape_index, ring, value_stamp, row_memo, base_cache strings. Implementation: a `memory_report()` method walking the structures with `capacity()`-based accounting; flag `--memory-report` enables the print. Test: run `{8,10,22}` control with the flag, assert a `MEMORY total=` line appears and subsystem lines sum to within 1% of total. Commit.

## Task 2: real-frontier baseline

Download the S3 v1 rowstate + cache to `sylver/move26_data/aws_frontier/` (immutable copies, hashes recorded). Run the instrumented engine with `--stop-after-evaluations <current+1>` + `--memory-report` on private copies; capture the baseline breakdown into `RUN_COMPACT_BASELINE.txt` (this file also receives all after-numbers as tasks land). No commit of the 756 MB artifacts — record hashes only; add path to `.gitignore` if needed. Commit the record.

## Task 3: serialization refactor + ring/stamp arenas

Introduce checkpoint v2 (new magic `v2`), keeping the complete v1 reader; loading v1 migrates in memory, saving always writes v2. Then replace per-shape `ring`/`value_stamp` vectors with flat arenas:

```cpp
    std::vector<signed char> ring_arena;   // sid * window_slots + slot
    std::vector<int> stamp_arena;
    signed char& ring_at(int sid, int slot) { return ring_arena[std::size_t(sid) * window_slots + slot]; }
    int& stamp_at(int sid, int slot) { return stamp_arena[std::size_t(sid) * window_slots + slot]; }
```

`register_shape` appends `window_slots` of (-1) to each arena. All `ring[sid][slot]` / `value_stamp[sid][slot]` sites mechanically become `ring_at`/`stamp_at`. The snapshot code reads through the same accessors. v2 serializes arenas as two flat blocks. Tests: full periodicity suite (checkpoint resume test now exercises v2 round-trip; the deterministic interrupt test exercises v1→v2 migration if pointed at a v1 file — add `test_v1_checkpoint_migrates`: generate a v1 rowstate with the reference binary built from HEAD~ during the test? No — simpler: commit a tiny v1 rowstate fixture for `{8,10,22}` generated before this task lands, stored as `tests/fixtures/ctl_810_22_v1.rowstate` + its cache; the test loads it with the new binary and recovers the period). Commit.

## Task 4: flat shape index

```cpp
    std::unordered_map<std::uint64_t, int> shape_hash_index;  // hash -> first sid
    std::vector<std::pair<std::uint64_t, int>> shape_hash_overflow;  // collisions
```

Key: splitmix-style hash over (eid, offsets values). `register_shape` looks up hash; on hit verifies `shapes[sid].eid == eid && offsets match` (offsets still readable per Task 5 layout); mismatch → scan overflow; true collision appends to overflow. `shape_index` (the std::map) is deleted; v2 does not serialize the index at all — it is rebuilt from shapes at load (deterministic, ~seconds), which also shrinks the rowstate. Tests: suite + a targeted unit asserting re-registration of an existing (eid, offsets) returns the same sid after a save/load cycle. Commit.

## Task 5: inline shape offsets

```cpp
    struct Shape {
        int eid;
        std::uint8_t offset_count;
        bool built;
        std::int16_t offsets_inline[7];
        std::int32_t offsets_spill = -1;      // index into spill arena when count > 7
        ...transitions per Task 6...
    };
    std::vector<std::int16_t> offset_spill_arena;
```

Accessor `offsets_of(sid) -> span-like view` used everywhere `shapes[sid].offsets` was read. Offsets fit int16 (they are bounded by top+tbar, hundreds). Assert on registration that values fit. v2 serializes count + values. Tests: suite; plus registration of a synthetic wide shape (>7 offsets) exercising spill. Commit.

## Task 6: compact transition specs

```cpp
    struct OddOption {                 // 8 bytes
        std::int32_t child;            // -1 while unregistered
        std::int16_t r;                // relative move (valid always)
        std::int16_t dmin;
    };
```

`build_transition_specs` computes each option's legality and dmin exactly as today but stores only (r, dmin); child offsets are recomputed transiently inside `evaluate`'s registration branch by re-deriving the canonical anchors from (parent offsets, r) — the identical arithmetic that today produces the stored vector, now in a scratch buffer. `even_children` stays `std::vector<int32_t>`. v2 serializes options as packed 8-byte records. This is the delicate task: the recomputation must reproduce the stored-offsets behavior exactly, including the absorption/canonicalization path and the "minimum anchor was absorbed" guard. Tests: suite (the `{8,10,22}` 50-shape certificate is a strong canary), plus the Task 8 equality control as the definitive gate. Commit.

## Task 7: memory re-measure

Re-run Task 2's baseline procedure on the compacted binary (v1 frontier → migrate → report). Append before/after table to `RUN_COMPACT_BASELINE.txt`; the headline is measured bytes/shape. Commit.

## Task 8: certification gates

1. **v1-vs-v2 equality control:** build reference binary from the pre-compaction commit; run both on `{8,10,22}` limit 201 and `{6,16}` limit 201 with fresh caches; assert identical stdout certificate lines and identical cache files. Wire as `test_compact_engine_matches_reference` (skips gracefully if git worktree unavailable).
2. Migration round-trip on the real 505 MB local v1 rowstate (private copy): load, advance one evaluation, save v2, reload v2, advance again; assert counters advance 1 each time.
3. ASan/UBSan interrupt-resume control on the compacted binary.
4. Full suite + `git diff --check`. Commit.

## Task 9: frontier migration + siege launch

Migrate the S3 frontier (private copy → v2, hashes recorded), then launch the home siege: `--exact-threads 10 --batch-pending 10000`, external 52 GB RSS guard via the SIGINT path, `RUN_COMPACT_SIEGE.txt` opened with the launch record. Monitor per established convention (persistent Monitor, `/proc/PID` liveness, terminal-signal grep). Block review after 5 days or terminal signal, whichever first.

## Self-review

Spec coverage: §1→Task 1-2, §2.1→Task 6, §2.2→Task 4, §2.3→Task 5, §2.4→Task 3, §3→Task 3 (+fixture test), §4→Task 8 (+suite per task), §5→Task 9. Placeholders: none — code sketches above are the load-bearing layouts; mechanical call-site edits are enumerated by compiler errors. Type consistency: accessors named once (`ring_at`, `stamp_at`, `offsets_of`) and used throughout.
