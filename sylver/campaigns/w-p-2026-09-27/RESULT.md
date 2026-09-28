# W={16,26,62,98} is P

**W is P.** Its last open obligation, move 108, is answered by **213**:
{16,26,62,98,108,213} is P. With it, every one of W's 52 Quiet End
obligations leads to an N-position. The same search found finite witnesses
for three obligations that had been covered only through infinite
P-positions: moves 72, 56 and 66. In particular, W no longer depends on
{16,26,62,72,82}, which the repository had taken from Sicherman's published
table, nor on B={16,26,56,62,66}. What the result still rests on is listed
under *Why this decides W*.

| Obligation | Reply | Destination | Frobenius | Native replay | Python replay |
| ---: | ---: | --- | ---: | --- | --- |
| 108 | 213 | {16,26,62,98,108,213} | 331 | P, 156,823,029 states, 1,264.16 s | P, 156,823,029 states, 9,855.92 s |
| 72 | 107 | {16,26,62,72,107} | 225 | P, 50,192,273 states, 353.73 s | P, 50,192,273 states, 2,972.04 s |
| 56 | 97 | {16,26,56,62,97} | 199 | P, 25,236,025 states, 164.04 s | P, 25,236,025 states, 1,603.41 s |
| 66 | 263 | {16,26,62,66,263} | 365 | P, 103,189,655 states, 707.80 s | P, 103,189,655 states, 5,842.68 s |

Each replay starts from an empty memo: the unchanged native source
(`aded19fa…`), freshly built by `sylver.verify_finite_reply`, and the
independent Python reference `sylver/solver.py` agree on P, the Frobenius
number, and the exact evaluated-state count. The destinations have gcd one,
so these refutations need no inherited outcome cache, infinite-position
certificate, or Quiet End Theorem.

## Why this decides W

W has gcd two, and its half {8,13,31,49} is a quiet ender, so W is a short
position: by the Quiet End Theorem, W is P exactly when each of its finitely
many **obligations** leads to an N-position. They are the 34 even moves 2g,
one for each gap g of the half, and the half's 18 odd gaps above 1: 52
moves. [audit.py](audit.py) lists them twice, with the arena referee's
profile (`sylver.arena.common.profile`) and with an independent coin-sum
count, checks both against the September 22 evidence graph, and accepts
exactly three kinds of evidence ([audit.json](audit.json)):

| Evidence | Obligations | Moves |
| --- | ---: | --- |
| Book certificate | 45 | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 30, 33, 34, 35, 38, 40, 41, 43, 44, 46, 50, 51, 54, 56, 59, 60, 67, 72, 76, 82, 86, 102, 134 |
| finite witness, native and Python replays | 5 | 66, 70, 92, 108, 118 |
| winning reply to a certified infinite P-position | 2 | 12, 36 |
| **total** | **52** | |

- **Book certificate:** a certificate in [The Book](../../arena/book/W.md),
  re-hashed against its digest and checked for its root, outcome N, and the
  current verifier profile; `python -m sylver.arena book verify` replays it
  with the fixed verifier.
- **Finite witness:** a campaign certificate for an odd reply and its
  receipt, whose native and Python runs both report P with the same state
  count; the certificate and transcripts are re-hashed against the receipt.
- **Certified node:** a winning reply to an infinite P-position that the
  repository itself certifies: {12,14,16}, a short cover in the September 5
  public release certificate (`publication/plan2-2026-09-05`, with its own
  `verify.py`), and V={16,26,36,56} (`short_certificates.py`, node V). The
  audit fails unless this kind covers exactly moves 12 and 36.

Every obligation is covered, so **W is P**. The claim rests on the Quiet
End Theorem (for W's own odd tail, and inside several of the certificates
above: the Book's covers for moves 4 and 20, and the certificates of
{12,14,16} and V), on the finite solvers and The Book's replays, and,
through moves 12 and 36 only, on three published P-positions that the
repository explicitly assumes: {12,14,16}'s certificate uses
{8,10,12,14}, a member of Blok's infinite pairing family, and V's uses
{8,10,12,14}, {8,12,26,30} (another member), and Sicherman's long
P-position {8,10,22}, whose odd tail the repository's periodicity engine
also recomputes.

## Consequences

- **Q={16,26,88,98} is N.** 88 = 26 + 62, so Q + 62 = W: from Q, naming 62
  reaches the P-position W.
- **U={16,26,88} P now needs only X={16,26,82,88} N.** The September 5
  verification report reduces U P to X N and Q N, resting on the project's
  earlier audit of U's other branches; Q N was the half that W settles. U P
  would make {16,26} N (88 answers 26). X, U, move 26, and opening 16
  remain unresolved.

No mathematical priority claim is made.

## Search

The witnesses were found by `sylver/parallel_solver.cpp` in shared-memo
sweeps: one memo for a batch of odd replies in increasing Frobenius order,
with several threads, so a candidate after the first reuses its
predecessors' positions. Move 108's sweep from reply 191 reached 213 in 5.4
minutes, where fresh single-threaded queries had cost about 15 minutes each.
That sweep predates the engine's memo check; its rows are in the
[w-one ledger](../w-one-2026-09-27/scan/ledger.jsonl) (engine `psw6`), made
by the w-one version of `sweep_w.py`. The later sweeps ran with
`--verify-memo` and the current [scan/sweep_w.py](scan/sweep_w.py); the
`ledger-*.jsonl` files record every query: position, Frobenius number,
outcome, the engine's winning move for N rows, cumulative batch states,
and whether the memo passed its check. Rows of a batch that ran out of
memory have `returncode` 1 and `memo_verified` false (an earlier version
of the script still marked them `ok`). The engine's source hash is not
recorded per row; the move-12, `{8,12,14}` and `{10,12,14,16}` sweeps used
the merged engine (after commit 224782d), the others an earlier build of
the same branch. Only P rows are independently replayed, and the claim
uses only those.

The sweeps skip replies whose positions the September 22 evidence graph or
the inherited exact cache already classify (`scan_w.known_outcomes`), so
the negative results combine both sources: every odd reply to move 12 up
to 977 is N (121–977 in `ledger-w12.jsonl`), every odd reply to move 36 up
to 401 is N (`ledger-w36.jsonl`), and so are the odd replies up to 301 of
{12,14,16}'s two pairing-family children, {8,12,14} and {10,12,14,16}
(121–301 in the `ledger-f*.jsonl` files). No finite witness for moves 12
and 36 was found.

## Evidence and reproduction

- `wM-certificate.json` and `verification/wM/`: each new certificate and its
  replay receipt with source and binary fingerprints, state counts, and
  transcript hashes.
- [audit.json](audit.json) from [audit.py](audit.py): the 52 obligations and
  their evidence.
- [w-frontier.json](w-frontier.json): the final summary, outcome P.

```sh
python sylver/campaigns/w-p-2026-09-27/audit.py > /tmp/w-audit.json
python -m sylver.arena book verify
python -m sylver.verify_finite_reply \
  --certificate sylver/campaigns/w-p-2026-09-27/w108-certificate.json \
  --output /tmp/w108-check --python --seconds 21600 --memory-gib 40
```

The move-108 Python replay needs about three hours on a busy host and up
to 24 GB.

## Later the same day

The Book raised its verification profile to 32 GB and admitted W's large
finite witnesses (moves 66, 70, 92, 108, 118) after one fresh replay each
by its fixed verifier; the replay counts equal the native and Python
counts of the campaign receipts (66: 103,189,655; 70: 79,594,540; 92:
80,500,948; 108: 156,823,029; 118: 115,933,058 states). The audit now
finds 50 obligations in The Book and the two certified nodes; the table
above records the evidence when W was first shown P.
