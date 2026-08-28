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
- **The move-26 program**: `{16,26}` is short; thirty of its 42 even
  children are refuted; the decisive child 88 reduces to the boundary
  question *is `X={16,26,82,88}` a P-position?* — where every odd reply
  through 407 and **all 32 even children of X are proved N**
  (`sylver/RUN_X_EVEN_FLANK.txt`).
- **The first size measurement of a g=2 periodicity computation of this
  class**: row X+409's dependency closure exceeds 3.15M translated
  shapes and 12.5M base-region exact positions, still unsaturated
  (`sylver/RUN_PERIODICITY_500H.txt`, `sylver/RUN_PERIODICITY_AWS.txt`);
  `{8,10,22}` needs 50 shapes for comparison.

No open problem is claimed solved: `X`, move 26, and the opening remain
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
