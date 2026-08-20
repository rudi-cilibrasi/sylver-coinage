# Periodicity Engine Parallel Fallbacks + Row-409 Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the g=2 ultimate-periodicity engine batch-parallel exact fallbacks and root-level hints (spec §3), verify nothing about its certificates changes, and resume the saved 220,574-shape row-409 frontier of X={16,26,82,88} at roughly 8x the historical single-thread pace (spec §4).

**Architecture:** The engine's row sweep gains a *collect mode*: `evaluate` becomes tri-state (P / N / unknown), an exact-cache miss in the base region enqueues the position instead of solving inline, unknown values are never written to the ring, row memo, or `first_p`, and the sweep repeats after each pending batch is solved by a worker-thread pool. Workers share nothing mutable — they receive precomputed generators and return results merged single-threaded. With `--exact-threads 1` (the default) the collect loop degenerates to today's exact single-pass behavior. The rowstate format is untouched: pending work is transient, so the existing version-1 checkpoint (505 MB, 220,574 shapes) loads unchanged.

**Tech Stack:** C++20 (`<thread>`, `<atomic>`, `<mutex>` additions), g++ `-O2/-O3 -Wall -Wextra -pedantic` warning-clean, Python unittest via the existing `run_engine` helper in `tests/test_sylver_periodicity.py`.

**Spec:** `docs/superpowers/specs/2026-08-19-sylver-move26-hybrid-design.md` §3–§4. Deviation from spec §3.3, justified: no rowstate v2 is needed because no field changes — the spec's own YAGNI rule ("if profiling proves need") applies to format churn too.

## Global Constraints

- "No outcome is ever inferred from search time, a finite prefix, or a heuristic."
- The period certificate must be a function of exact outcomes only. Unknown (-1) values must never reach `ring`, `row_memo`, `first_p`, `base_p_hits`, or a snapshot. The snapshot code already hard-exits on an incomplete window (`periodicity_engine.cpp:1218-1222`) — that guard stays.
- `--exact-threads 1` must reproduce today's behavior exactly; all seven existing periodicity tests must pass unmodified.
- Worker threads share no mutable state: main thread precomputes generators/Frobenius, workers solve pure positions, main thread merges results, updates counters, and saves the cache atomically.
- Hints are outcome-invariant reordering only (the flank campaign's proven mechanism); the hint pool is engine-internal and never persisted.
- Campaign block: 7180 minutes under `timeout --signal=INT`, 8 threads initially, RSS watched; the run record follows the cumulative naming convention (`RUN_PERIODICITY_600H.txt`).
- Commits on `master`, sentence-case imperative subject, trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## File Structure

- Modify: `sylver/periodicity_engine.cpp` — tri-state `evaluate`, `exact_or_collect`, `solve_pending_parallel`, hint plumbing in the embedded `ExactSolver`, `--exact-threads` flag, collect loop in `main`.
- Test: `tests/test_sylver_periodicity.py` — thread-invariance of all four period certificates, cache-content equality, flag validation.
- Campaign artifacts (Task 3): `sylver/move26_data/periodicity_parallel_run.log`, later `sylver/RUN_PERIODICITY_600H.txt`.

---

### Task 1: batch-parallel exact fallbacks with hints, behind `--exact-threads`

**Files:**
- Modify: `sylver/periodicity_engine.cpp`
- Test: `tests/test_sylver_periodicity.py`

**Interfaces:**
- Consumes: existing `Engine` internals read this session — `evaluate` (line ~1088), `exact_outcome` (line ~989), `cached_outcome`, `position_generators`, `generator_key`, `exact_frobenius`, `solve_exact_position`, `ExactResult`, the sweep/backfill loop in `main` (lines ~1373-1397), `run_engine` test helper.
- Produces: CLI flag `--exact-threads N` (1..64, default 1). No other observable interface change; certificates identical for any N.

- [ ] **Step 1: Write the failing tests**

Append to `NativePeriodicityTests` in `tests/test_sylver_periodicity.py`:

```python
    def test_exact_threads_reproduce_all_period_certificates(self) -> None:
        cases = (
            ((2,), "PERIOD start=5 length=4 shapes=1", ("P-HIT n=3",)),
            ((4, 6), "PERIOD start=9 length=4 shapes=3", ()),
            ((6, 16), "PERIOD start=57 length=4 shapes=2", ("P-HIT n=7",)),
            ((8, 10, 22), "PERIOD start=49 length=8 shapes=50", ()),
        )
        for base, period, hits in cases:
            with self.subTest(base=base):
                output = self.run_engine(201, base, ("--exact-threads", "4"))
                self.assertIn(period, output)
                self.assertEqual(
                    tuple(line for line in output if line.startswith("P-HIT")),
                    hits,
                )

    def test_exact_threads_serial_and_parallel_caches_agree(self) -> None:
        outcomes = {}
        for label, threads in (("serial", "1"), ("parallel", "4")):
            cache = Path(self.tempdir.name) / f"threads-{label}.cache"
            subprocess.run(
                [
                    str(self.binary),
                    str(cache),
                    "201",
                    "--exact-threads",
                    threads,
                    "8",
                    "10",
                    "22",
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=60,
            )
            rows = {}
            for line in cache.read_text().splitlines():
                key, _, value = line.rpartition(" ")
                rows[key] = value
            outcomes[label] = rows
        self.assertEqual(outcomes["serial"], outcomes["parallel"])

    def test_exact_threads_rejects_invalid_counts(self) -> None:
        for bad in ("0", "-2", "65", "x"):
            cache = Path(self.tempdir.name) / "bad-threads.cache"
            completed = subprocess.run(
                [str(self.binary), str(cache), "31", "--exact-threads", bad, "4", "6"],
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=30,
            )
            self.assertNotEqual(completed.returncode, 0)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m unittest -k exact_threads tests.test_sylver_periodicity -v 2>&1 | tail -8`
Expected: all three FAIL (unknown option `--exact-threads` exits 1 → `CalledProcessError`; the rejects-invalid test fails because exit 1 happens for valid counts too — assertion inverted only after implementation).

- [ ] **Step 3: Implement**

3a. Includes: add `#include <atomic>`, `#include <thread>` to the include block.

3b. Extend `ExactResult` and the solve helpers with the winning move and hints (the same outcome-invariant root reordering proven in `native_solver.cpp`):

```cpp
struct ExactResult {
    bool is_p;
    int winning_move;   // 0 when P
    std::size_t states;
};
```

In `ExactSolver`, add above `winning_move`:

```cpp
    [[nodiscard]] int solve(const std::vector<int>& hints) {
        if (const auto found = memo_.find(initial_); found != memo_.end())
            return found->second;
        for (const int hint : hints) {
            if (hint < 2 || hint > frobenius_ || initial_.test(hint)) continue;
            if (winning_move(adjoin(initial_, hint)) == 0) {
                memo_.emplace(initial_, static_cast<std::uint16_t>(hint));
                return hint;
            }
        }
        return winning_move(initial_);
    }
```

and change `solve()` callers accordingly:

```cpp
template <std::size_t Words>
ExactResult solve_exact_with_words(
    const std::vector<int>& generators, int frobenius,
    const std::vector<int>& hints
) {
    ExactSolver<Words> solver(generators, frobenius);
    const int move = solver.solve(hints);
    return {move == 0, move, solver.states_evaluated()};
}

ExactResult solve_exact_position(
    const std::vector<int>& generators, int frobenius,
    const std::vector<int>& hints = {}
) { ...same width dispatch, passing hints... }
```

3c. Engine members (near the base-cache block):

```cpp
    int exact_threads = 1;
    bool collect_mode = false;
    std::vector<std::pair<std::string, std::vector<int>>> pending;
    std::set<std::string> pending_keys;
    std::vector<int> hint_pool;  // recent distinct winners, outcome-invariant reordering only
```

3d. Collect-aware exact access (next to `exact_outcome`; `exact_outcome` itself gains the hint pass and winner recording so the serial path benefits too):

```cpp
    signed char exact_or_collect(int eid, const std::vector<int>& anchors) {
        std::vector<int> gens = position_generators(eid, anchors);
        const std::string key = generator_key(gens);
        if (const auto it = base_cache.find(key); it != base_cache.end())
            return it->second ? 1 : 0;
        if (!collect_mode) return exact_outcome(eid, anchors) ? 1 : 0;
        if (pending_keys.insert(key).second)
            pending.emplace_back(key, std::move(gens));
        return -1;
    }

    void record_hint(int winner) {
        if (winner <= 0) return;
        for (const int existing : hint_pool)
            if (existing == winner) return;
        hint_pool.push_back(winner);
        if (hint_pool.size() > 16)
            hint_pool.erase(hint_pool.begin());
    }
```

In `exact_outcome`, pass `hint_pool` to `solve_exact_position` and call `record_hint(exact.winning_move)` after merging.

3e. Tri-state `evaluate`. Exact edits, in order:

- Replace the base-region branch:

```cpp
        } else if (m < auto_min) {
            result = exact_or_collect(shapes[sid].eid, anchors);
            if (result < 0) return -1;  // pending exact dependency; write nothing
        } else {
```

- In the odd-options loop, add `bool saw_unknown = false;` before the loop and change the child handling:

```cpp
                    if (cv == 1) { winning = true; break; }
                    if (cv < 0) saw_unknown = true;
```

- Same two lines in the even-children loop (declare `saw_unknown` once, before the odd loop).
- Immediately before `result = winning ? 0 : 1;`:

```cpp
            if (!winning && saw_unknown) return -1;  // no ring/memo/first_p writes
```

A parent with a P child is decided N even when a sibling is unknown — that pruning is free work saved. Unknown never reaches `ring`, `row_memo`, or `first_p`, so snapshots and P-HIT stay exact-outcome-only.

3f. Batch solver (Engine method). Workers receive frozen inputs and write only their own slot; merge is single-threaded:

```cpp
    void solve_pending_parallel() {
        struct Item {
            std::string key;
            std::vector<int> gens;
            int frobenius = 0;
            bool done = false;
            ExactResult result{};
        };
        std::vector<Item> items;
        items.reserve(pending.size());
        for (auto& [key, gens] : pending) {
            Item item;
            item.key = key;
            item.gens = std::move(gens);
            item.frobenius = exact_frobenius(item.gens);
            if (item.frobenius > kMaximumFrobenius) {
                std::cerr << "base position exceeds solver capacity: "
                          << item.key << "\n";
                std::exit(2);
            }
            items.push_back(std::move(item));
        }
        pending.clear();
        pending_keys.clear();
        const std::vector<int> hints = hint_pool;  // frozen per batch
        std::atomic<std::size_t> next{0};
        std::vector<std::thread> pool;
        const std::size_t width =
            std::min<std::size_t>(static_cast<std::size_t>(exact_threads),
                                  items.size());
        for (std::size_t t = 0; t < width; ++t)
            pool.emplace_back([&]() {
                for (;;) {
                    const std::size_t i = next.fetch_add(1);
                    if (i >= items.size() || interrupt_requested != 0) return;
                    try {
                        items[i].result = solve_exact_position(
                            items[i].gens, items[i].frobenius, hints);
                        items[i].done = true;
                    } catch (const CampaignInterrupted&) {
                        return;
                    }
                }
            });
        for (std::thread& worker : pool) worker.join();
        for (const Item& item : items) {
            if (!item.done) continue;
            ++exact_completed;
            exact_states += item.result.states;
            base_cache[item.key] = item.result.is_p;
            record_hint(item.result.winning_move);
            if (item.frobenius >= 180)
                std::cout << "EXACT end key=" << item.key
                          << " outcome=" << (item.result.is_p ? "P" : "N")
                          << " states=" << item.result.states << std::endl;
            else if (exact_completed % 1000 == 0)
                std::cout << "EXACT progress completed=" << exact_completed
                          << " states=" << exact_states
                          << " cache=" << base_cache.size() << std::endl;
        }
        dirty_cache = true;
        save_cache();
        throw_if_interrupted();  // completed work is merged; now honor the signal
    }
```

3g. CLI parsing in `main` (next to `--stop-after-evaluations`):

```cpp
        } else if (argument == "--exact-threads") {
            if (++i >= argc) {
                std::cerr << "--exact-threads requires a count\n";
                return 1;
            }
            try {
                std::size_t parsed = 0;
                const std::string count = argv[i];
                const long threads = std::stol(count, &parsed);
                if (parsed != count.size() || threads < 1 || threads > 64)
                    throw std::invalid_argument("count");
                eng.exact_threads = static_cast<int>(threads);
            } catch (const std::exception&) {
                std::cerr << "invalid --exact-threads count\n";
                return 1;
            }
        }
```

3h. Collect loop in `main`, replacing the sweep body inside the existing `try` (the `catch (const CampaignInterrupted&)` block is untouched):

```cpp
            try {
                for (;;) {
                    eng.collect_mode = eng.exact_threads > 1;
                    eng.pending.clear();
                    eng.pending_keys.clear();
                    size_t count = eng.shapes.size();
                    for (size_t sid = 0; sid < count; ++sid)
                        eng.evaluate(static_cast<int>(sid), static_cast<int>(n));
                    while (count < eng.shapes.size()) {
                        ...existing backfill loop, byte for byte...
                    }
                    if (eng.pending.empty()) break;
                    std::cout << "EXACT-BATCH n=" << n
                              << " pending=" << eng.pending.size()
                              << " threads=" << eng.exact_threads << std::endl;
                    eng.solve_pending_parallel();
                }
                throw_if_interrupted();
            } catch (const CampaignInterrupted&) {
```

With `exact_threads == 1`, `collect_mode` stays false, `pending` stays empty, the loop runs once: today's behavior exactly.

- [ ] **Step 4: Compile warning-clean and run the periodicity suite**

Run: `g++ -std=c++20 -O2 -Wall -Wextra -pedantic sylver/periodicity_engine.cpp -o <scratchpad>/pe_check 2>&1 | head` — expect silence.
Run: `python -m unittest tests.test_sylver_periodicity -v 2>&1 | tail -8` — expect all 10 (7 old + 3 new) PASS.

- [ ] **Step 5: Commit**

```bash
git add sylver/periodicity_engine.cpp tests/test_sylver_periodicity.py
git commit -m "Solve periodicity exact fallbacks in hinted parallel batches

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: pre-launch verification gates

No new code — three verifications that must pass before real compute is spent.

- [ ] **Step 1: ASan/UBSan interrupt-resume control with threads**

```bash
S=<scratchpad>
g++ -std=c++20 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
    sylver/periodicity_engine.cpp -o "$S/pe_asan"
cd "$S" && rm -f asan.cache asan.cache.rowstate
"$S/pe_asan" "$S/asan.cache" 201 --exact-threads 4 --stop-after-evaluations 25 8 10 22; echo "exit: $?"
"$S/pe_asan" "$S/asan.cache" 201 --exact-threads 4 8 10 22 | grep -E "PERIOD|P-HIT"
```

Expected: first run exits 75 after saving a row checkpoint; second resumes and prints `PERIOD start=49 length=8 shapes=50`, no sanitizer reports.

- [ ] **Step 2: isolated-copy resume of the real 505 MB rowstate**

The standard routine from every prior campaign, now with the new binary, the flank-merged cache, and threads:

```bash
S=<scratchpad>; mkdir -p "$S/resume_check"
cp sylver/move26_data/periodicity_x.cache "$S/resume_check/"
cp sylver/move26_data/periodicity_x.cache.rowstate "$S/resume_check/"
g++ -std=c++20 -O2 -Wall -Wextra -pedantic sylver/periodicity_engine.cpp -o "$S/pe_campaign"
"$S/pe_campaign" "$S/resume_check/periodicity_x.cache" 409 \
  --base-record sylver/move26_data/full_82.txt \
  --base-record sylver/move26_data/x_sortie.txt \
  --exact-threads 8 --stop-after-evaluations 22641269 \
  16 26 82 88 | tail -5; echo "exit: $?"
```

Expected: `ROW-CHECKPOINT loaded ... shapes=220574 ... evaluations=22641268`, exactly one more evaluation, a new checkpoint saved, exit 75. This proves the v1 rowstate loads unchanged, its dependency subset survives the flank merge, and the collect loop coexists with resume.

- [ ] **Step 3: record fingerprints**

`sha256sum sylver/periodicity_engine.cpp "$S/pe_campaign" sylver/move26_data/periodicity_x.cache sylver/move26_data/periodicity_x.cache.rowstate` — preserve for the run record.

---

### Task 3: launch the row-409 resume campaign

- [ ] **Step 1: launch (5-day block, 8 threads)**

```bash
cp <scratchpad>/pe_campaign /tmp/conway-sylver-periodicity-600h
nohup timeout --signal=INT --kill-after=600s 7180m \
  stdbuf -oL -eL /tmp/conway-sylver-periodicity-600h \
  sylver/move26_data/periodicity_x.cache 409 \
  --base-record sylver/move26_data/full_82.txt \
  --base-record sylver/move26_data/x_sortie.txt \
  --exact-threads 8 \
  16 26 82 88 \
  > sylver/move26_data/periodicity_parallel_run.log 2>&1 &
```

The engine loads the row-409 checkpoint automatically from `periodicity_x.cache.rowstate` and saves it atomically on the INT at budget end.

- [ ] **Step 2: arm monitoring**

Watch for every terminal and every actionable signal, not just success: `P-HIT` (X is N — campaign victory, go to the spec's certification path with the concrete child-98 re-verification), `PERIOD` (odd tail closed — with the banked even flank, X is P), `ROW-CHECKPOINT saved` (block ended), `error|exceeds|conflicts` (abort states), plus an RSS check (threads make multi-GB solver memos possible; if RSS approaches ~45 GB, note it and plan the next block at fewer threads).

- [ ] **Step 3: block review (after the run ends or fires a signal)**

Compare against the 480H baseline (24,815 outcomes, 22,082 shapes, 3.26M evaluations per 5-day block): outcomes added, shapes added, evaluations advanced, exact states/second. Write `sylver/RUN_PERIODICITY_600H.txt` in the established format (command, fingerprints, markers, audit, resume verification), update RESEARCH.md/STATUS.md/QUEUE.md, commit. If two consecutive blocks decelerate without convergence, trigger the spec's pivot rule (including the community option) before block three.

---

## Plan Self-Review (completed)

- **Spec coverage:** §3.1 batch-and-resweep → Task 1 (3c–3h); §3.2 hints → Task 1 (3b, 3d); §3.3 checkpoint compatibility → satisfied with zero format change + Task 2 Step 2 proof; §3.4 state-count semantics → counters unchanged, per-implementation note in run record; §3 gates → Task 1 Step 4 + Task 2; §4 resume/timebox/pivot → Task 3.
- **Placeholder scan:** the backfill loop is referenced "byte for byte" rather than duplicated — it is the existing code at lines 1377-1397, moved unmodified inside the collect loop; no TBDs.
- **Type consistency:** `ExactResult{is_p, winning_move, states}` threaded through both solve helpers and both call sites (`exact_outcome`, `solve_pending_parallel`); `exact_or_collect` returns `signed char` matching `evaluate`'s result type.
