# W's moves 86 and 92 are answered by 129 and 139

**{16,26,62,86,98,129} is P** (Frobenius number 237) and
**{16,26,62,92,98,139} is P** (Frobenius number 241). After move 86 from
W={16,26,62,98}, playing **129** wins; after move 92, playing **139** wins.

| Destination | Frobenius | Native replay | Python replay |
| --- | ---: | --- | --- |
| {16,26,62,86,98,129} | 237 | P, 68,758,240 states, 478.21 s | P, 68,758,240 states, 3,307.21 s |
| {16,26,62,92,98,139} | 241 | P, 80,500,948 states, 548.48 s | P, 80,500,948 states, 4,671.30 s |

Each replay starts from an empty memo. The native solver is the unchanged
repository source (`aded19fa…`), freshly built by
`sylver.verify_finite_reply`, and the Python solver is the independent
reference `sylver/solver.py`. For each destination the two agree on P,
the Frobenius number, and the exact evaluated-state count. The
destinations have gcd one, so these refutations need no inherited outcome
cache, infinite-position certificate, or Quiet End Theorem.

W now has **49 of 52 obligations covered**. These three moves remain open:

**70, 108, 118**

W, Q, X, move 26, and opening 16 remain unresolved. W P would establish
Q={16,26,88,98} N (Q+62 = W); U={16,26,88} P would still also need
X={16,26,82,88} N. No mathematical priority claim is made.

## Evidence and reproduction

- [w86-certificate.json](w86-certificate.json) and
  [w92-certificate.json](w92-certificate.json): the legal two-move paths and
  their canonical finite P destinations.
- [verification/](verification/): replay receipts with source and binary
  fingerprints, state counts, and transcript hashes.
- [scan/ledger.jsonl](scan/ledger.jsonl): every discovery query, and
  [audit.json](audit.json): the structural audit of the ledger.
- [w-frontier.json](w-frontier.json): the 49/52 summary linked to the
  certificates and receipts by hashes.

From the repository root, with new output directories:

```sh
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-three-2026-09-27/w86-certificate.json \
  --output /tmp/w86-check --python --seconds 10800 --memory-gib 40
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-three-2026-09-27/w92-certificate.json \
  --output /tmp/w92-check --python --seconds 10800 --memory-gib 40
```

Each Python replay needs about an hour and up to 16 GB.

## Search result and continuation

The scan ledger records 149 queries; the audit found no structural
failures. It refuted 113 further odd replies (single native runs, with the
solver's winning move recorded) and found the two P destinations above.
Queries that exceeded memory are recorded as failures and were retried.

The ledger also contains one more P destination, found near the end of this
snapshot: **{16,26,62,70,98,169}** (79,594,540 states in its single discovery
run). Its independent replay was in progress when this record was made, so
move 70 stays open here, in [w-frontier.json](w-frontier.json), and in
[audit.json](audit.json), which lists it as pending replay.

The first unclassified odd replies in the remaining branches are listed in
[audit.json](audit.json). They are starting points, not bounds: a finite
prefix of N outcomes does not prove any of these infinite positions P.
