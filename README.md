# Sylver Coinage after opening 16 — a machine-verified campaign

**▶ [Live demo](https://rudi-cilibrasi.github.io/sylver-coinage/):**
play Sylver Coinage against the exact solver in your browser, and query
the campaign's 273,000-outcome cache directly from this repository.

This repository is the complete, auditable record of a computational
campaign on **Sylver Coinage after the opening move 16** (Conway's prize
question: does 16 have a winning reply, and which?).  Every claim below
is backed by artifacts in this history: two independent solver
implementations that agree on outcomes *and* exact evaluated-state
counts, SHA-256-fingerprinted run records, and a conflict-checked cache
of 267,000+ exact position outcomes whose cumulative solver work
exceeds 10^12 states.

## Headline results

- **W frontier reduced to five moves:** after move 102 from
  `W={16,26,62,98}`, reply **95** reaches the finite P-position
  `{16,26,62,95,98,102}`. Fresh native and Python replays agree on P,
  Frobenius number 203, and exactly **44,985,582 states**. W now has
  **47 of 52 obligations covered**, with **70,86,92,108,118** remaining.
  See the [result and reproducible certificate](sylver/campaigns/w-six-2026-09-22/RESULT.md).
- **Earlier W continuation (September 22):** after move 134 from
  `W={16,26,62,98}`, reply **85** reaches the finite P-position
  `{16,26,62,85,98,134}`. Independent native and Python replays agree on
  the P outcome and exact count of 37,192,385 states, without inherited
  outcome assumptions. This left six
  W moves unresolved before the move-102 result above. See the
  [September 22 continuation and reproducible certificate](sylver/campaigns/w-seven-2026-09-22/RESULT.md).
- **September 22 certificate:** `{16,26,56,62,66}` is P, with all 40
  obligations covered. The last move, 76, is answered by 247. A fresh
  replay checks all 69 finite leaves without the campaign cache; six
  established infinite certificates remain explicit dependencies. This
  answers move 66 from `W={16,26,62,98}` with 56 and left seven W moves
  unresolved before the continuation above. See the [result, response table, and reproduction command](sylver/campaigns/targeted-2026-09-22/RESULT.md).
- **September 5 verification release:** independent confirmation of the
  published P-position `{16,26,54,60,62}`, with all 38 root obligations
  covered. The [report and reproducibility bundle](sylver/publication/plan2-2026-09-05/README.md)
  include a fresh public reconstruction, 62 recomputed finite leaves,
  41 matching Python cross-checks, and 27 passing tests. The certificate
  names its three published P-position dependencies explicitly.
  [Download the archive](sylver/publication/plan2-2026-09-05.tar.gz)
  ([SHA-256](sylver/publication/plan2-2026-09-05.tar.gz.sha256)).
- **A certified response table answering every even move 2–24 after
  opening 16** (odd moves lose by Hutchings' theorem).  Includes
  independent confirmations of published claims by G. Sicherman and
  T. Blok: `{16,20,34}` (answers move 20), `{10,16,24}` (answers move
  24), the `{8,10,22}` ultimate-periodicity certificate, and a
  machine-checked audit of Blok's `{8,12}` pairing theorem.
- **`{12,16,20}` is an N-position via the even reply 8**
  (`<12,16,20,8> = <8,12>`), completing a step left open in Blok's 2021
  g=2 report.  See `sylver/eight_twelve.py` and `sylver/RESEARCH.md`
  (Attempt 5).
- **Six apparently new P-positions, plus an independent confirmation
  of a seventh**: the certified node `{16,26,36,56}` turns out to
  appear on G. Sicherman's online P-position table (our thanks for the
  correction), making this campaign's full finite certificate for it an
  unwitting independent verification; the other six await priority
  checks against T. Blok's unpublished analyses.  Full certificates in
  `sylver/short_certificates.py` and the `RUN_*.txt` records.
- **The move-26 program, corrected September 5**: `{16,26}` is short;
  thirty of its 42 even children are refuted. Its child
  `U={16,26,88}` is P iff **both** `X={16,26,82,88}` and
  `Q={16,26,88,98}` are N. The previous reduction to X alone was
  unsupported. Every odd reply to X through 407 and **all 32 even
  children of X are proved N** (`sylver/RUN_X_EVEN_FLANK.txt`).
  See the [correction and counterexample](sylver/publication/plan2-2026-09-05/REPORT.md#correction-to-the-opening-16-reduction).
- **The first size measurement of a g=2 periodicity computation of this
  class**: row X+409's dependency closure exceeds 3.15M translated
  shapes and 12.5M base-region exact positions, still unsaturated
  (`sylver/RUN_PERIODICITY_500H.txt`, `sylver/RUN_PERIODICITY_AWS.txt`);
  `{8,10,22}` needs 50 shapes for comparison.

No open problem is claimed solved: `X`, `Q`, move 26, and the opening remain
undecided.  See `sylver/RESEARCH.md` for the complete attempt-by-attempt
log, including negative results and two soundness bugs found and fixed
by the audit discipline.

## Verifying

```sh
python -m unittest discover -s tests          # full suite
python -m sylver.solver 16 6                  # exact finite evaluator
g++ -std=c++20 -O2 -Wall -Wextra -pedantic -pthread \
    sylver/periodicity_engine.cpp -o engine
./engine /tmp/ctl.cache 201 8 10 22           # reproduces the published
                                              # PERIOD start=49 length=8
```

The deep-certificate suite recomputes every claimed P-position; state
counts are deterministic and must match the run records exactly.

## Repository map

| Path | Contents |
| --- | --- |
| `sylver/solver.py` | exact finite evaluator (Python reference) |
| `sylver/native_solver.cpp` | the same recurrence in C++ (differentially tested) |
| `sylver/periodicity_engine.cpp` | g=2 ultimate-periodicity engine: checkpointed, parallel exact fallbacks, compact v2 representation |
| `sylver/short_certificates.py` | the certified P-node graph and opening-16 table |
| `sylver/publication/plan2-2026-09-05/` | verification report, public certificate, source snapshot, and reproduction instructions |
| `sylver/campaigns/` | September 22 certificates, bounded experiments, verification receipts, and remaining obligations |
| `sylver/RESEARCH.md` | the full research log (Attempts 1–23) |
| `sylver/RUN_*.txt` | fingerprinted run records for every campaign |
| `sylver/move26_data/` | exact outcome cache (267,847 rows) and scan artifacts |
| `tests/` | 60+ unit and differential tests |
| `docs/superpowers/` | design specs and implementation plans for each campaign |

## Large artifacts

This public history is filtered from a larger private research
repository: only Sylver Coinage material is included, and one file —
the 505 MB version-1 periodicity row checkpoint — is distributed as a
release asset rather than a git blob (its SHA-256,
`cd2a912587395e221d4956236db365f74a2c474d855c2d28d0e45551008a1c28`, is
pinned in the run records).  Source-file SHA-256 fingerprints cited in
`RUN_*.txt` records are content hashes and remain verifiable in this
history.

## Author

Rudi Cilibrasi (<rudi@metagood.com>), with campaign engineering by
Claude (Anthropic) and GPT 5.6 Sol (OpenAI).  AI subscriptions
generously provided by [Metagood.com](https://metagood.com).
Independent confirmation or refutation of any result is warmly
invited.
