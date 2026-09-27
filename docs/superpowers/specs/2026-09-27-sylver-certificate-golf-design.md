# Certificate golf and The Book

Date: 2026-09-27
Status: approved design (autonomous session; the owner pre-authorized
design decisions and asked that work proceed without pausing)

## Context

The owner's first competition: programs make **short certificate proofs
based on the database already calculated**, and we see which do it more
efficiently or quickly. "Let us open the Book" — Erdős's Book of perfect
proofs — names the product: for every result we care about, the shortest,
cheapest-to-check proof anyone has found.

The proof arena (PR #14) already has what a fair contest needs: a closed
proof language, canonical bytes `C`, a fixed fresh verifier, process-tree
CPU accounting, and the agreed score `S=(C+100)*(T+1)`. Its pilot ended with
"revise": the tasks were toys (`{4,5}`, `{6,7}`) whose timings were
dominated by process start-up, and competitors could not use the database.

A measurement motivates the contest. For ten N-positions sampled from the
305,011-row cache (Frobenius 130–200), the verifier's own root search cost
about the same as proving the cheapest database-known P child in seven
cases, but **2–3× more** in three (for `{16,26,70,82,88,97,131,153}`,
23.2M states from the root versus 9.9M via reply 53). Choosing the proof's
structure matters, and the database is what makes good choices cheap.

## What changes

### 1. Hints: the database as an untrusted oracle

A **hint file** is a gzip of sorted canonical lines `KEY OUTCOME`
(`16,26,38,...  P`), content-addressed by the SHA-256 of its uncompressed
bytes and stored as `hints/SHA.txt.gz` beside the bundles. The frozen hint
set is the historical 305,011-row cache plus every P/N fact of the post-PR13
campaign evidence graph: 308,322 facts.

A hint is **never** a proof dependency. It does not enter the trusted
snapshot, cannot be cited by a `baseline` node, and never enters the
session's proof nodes. A certificate built from hints is valid only if the
fixed verifier replays every finite leaf; a wrong hint makes a proof
invalid, never a false theorem.

### 2. Golf challenges

A new challenge kind, **`golf`**, whose outcome is public (it is stated in
the manifest context) and whose manifest carries an optional `hints` digest.
Golf bundles have an empty trusted snapshot apart from the fixed theorem
library, so the whole certificate is counted in `C` and replayed in `T`.
Only `golf` manifests may carry hints. Old bundles remain valid under their
own pinned verifier; this is a new verifier version, as any change to
`snapshot.py` is.

### 3. Protocol

`hint` with `positions` (1–4096) returns `P`, `N`, or `unknown` for each,
labelled `untrusted-hint`. The hint file loads lazily on the first call, and
that CPU is charged like all discovery work. Sessions without hints answer
`unknown`.

### 4. Golf policies (bounded DSL, no arbitrary code)

New `strategy` values, sharing the existing policy fields:

| Strategy | Certificate |
| --- | --- |
| `golf-root` | A single `finite` leaf for a gcd-one target (the outcome is taken from hints, else one exact query). Minimal `C`; the verifier searches from the root. |
| `golf-witness` | N target: `edge` to the hinted finite P child with the fewest gaps (then smallest Frobenius), whose `finite` leaf is replayed. P target: a root leaf. |
| `golf-probe` | N target with a choice: races bounded exact queries (charged) over up to `batch_size` hinted witnesses and then the root, each capped by the time that could still beat the best estimate, and certifies the cheapest measured option, never a witness its probe refuted. P target: a root leaf. |
| `golf-blind` | Hint-free control: computes a finite target's outcome exactly; searches up to `rounds` odd replies for a gcd-two target's witness. |

P targets always get a root leaf. A one-level cover multiplies `C` by
roughly 50–100 (one row, edge, and leaf per legal move), so under the
agreed product it wins only if checking becomes 50–100 times cheaper; the
N-target measurement above shows witness choice changing cost by 2–3
times, not by two orders of magnitude. Covers remain available to external
competitors through the protocol.

### 5. Golf panel

The panel is predeclared in code, chosen once by a seeded draw from the
database and recorded with each target's **deterministic** root-search state
count (not a timing), so the selection is reproducible on any machine:

- **Tier A** — Frobenius 100–150, 3 P + 3 N, root search at most 2M states.
- **Tier B** — Frobenius 150–200, 3 P + 3 N, root search 0.5M–8M states, so
  that structure, not process start-up, dominates the score.
- **Tier C (research)** — the campaign's own refutations around W: moves 134
  and 102 (gcd two, so only a witness can certify them; replies 85 and 95),
  the finite pair after 102 and 89 (root search 6,382,154 states against
  1,721,485 for the hinted witness 33), and that witness's P destination.
  Tier C needs a 16 GiB memory profile and minutes of CPU per episode.

**Revision after measurement.** The first draw took N targets at random and
found that only 3 of 8 had *any* hinted P child: the campaign database
records outcomes, not winning moves, so for most positions it offers no
witness choice at all. N targets are therefore drawn among database N
positions with at least one hinted P child (the same seed), because only
there does the database create a certification choice; P targets remain
root-leaf controls. Recording witnesses, not just outcomes, is a
recommendation for future campaigns.

Every golf target is public: the database is a public artifact, so prior
exposure is total and golf measures certification efficiency, not
discovery.

### 6. The Book

`sylver/arena/book/` holds `index.json`, `BOOK.md`, and canonical
certificates named by their SHA-256. `python -m sylver.arena book add
EPISODE...` re-verifies an episode's certificate in a fresh verification run
(never trusting the episode's own receipt), measures verification CPU and the
verifier's **deterministic evaluated-state count**, and records it under its
target. `book verify` replays every entry; `book render` writes `BOOK.md`.

Per target the Book lists every admitted certificate with `C`, states,
verification CPU, and the source episode's full `S` when one exists. Its
**entry of record** is the certificate with the lowest verification-only
product `(C+100)*(V+1)`, where `V` is the median of three curator
re-verifications, labelled as such: it prices a proof by what it costs to
*check*, excluding the discovery cost that tournament scores include. Ties
within 2% go to fewer states, then fewer bytes. The Book never replaces a
tournament score and states for each entry the profile it was measured on.

### 7. Golf tournament report

`python -m sylver.arena golf-pilot` builds the panel, runs the four golf
strategies and the pre-existing `interleaved` baseline on tiers A and B with
three repetitions (tier C once), admits every distinct valid certificate to
a fresh Book, and renders per-target leaderboards. Winner tallies count only
targets that received more than one distinct certificate. The recorded
report adds a curator's findings and decision section, marked as such.

**Book rule (revised after review).** Timing noise between runs of the same
certificate reached tens of percent, so the entry of record minimizes the
deterministic checking cost `(C+100)*(states/RATE+1)` with a fixed
`RATE = 100,000` verifier states per second; measured CPU is informational,
and entries are compared only under one verifier version.

## Error handling

Malformed or tampered hint files (wrong digest, unsorted, bad outcome
token, duplicate key) are rejected at load, making the episode invalid
rather than silently empty. Unknown positions return `unknown`. A golf
policy whose hinted outcome is wrong submits a certificate that fails
verification: invalid, no score. `book add` refuses invalid, over-budget, or
non-golf episodes and any certificate whose replay disagrees.

## Testing

- Hint files: canonical, digest-checked, sorted; tamper and duplicate
  rejection; lookup equals a dict built from the same rows.
- Hints never become proof nodes: a proof citing a hinted position as
  `baseline` is rejected; a false hint yields an invalid episode.
- Manifests: only `golf` may carry hints; the target must not be in the
  trusted snapshot; old manifests still validate.
- Policies: each golf strategy produces a valid certificate for small
  golf targets; `golf-witness` picks the hinted P child with the fewest gaps;
  `golf-probe` certifies a cheaper witness than the root on a database
  target where the root search is measurably costlier.
- Book: add/verify/render round trip; refusal of invalid episodes;
  entry-of-record ordering.

## Non-goals

No change to the score, the proof rules, or the finite verifier; no new
theorem; no real-model calls; no claim that golf results are new
mathematics. A golf certificate for a public result is an independent,
cheaper-to-check proof of that result, and the Book says exactly that.
