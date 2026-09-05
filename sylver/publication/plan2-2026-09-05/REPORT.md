# Independent verification and a corrected reduction in Sylver Coinage

Research note and reproducibility bundle, 5 September 2026.

We independently confirm that **{16,26,54,60,62} is a P-position**,
using exact finite computations, complete move coverage, and established
infinite-position results. This confirms an existing entry on
[Sicherman's P-position list](https://sicherman.net/sylver/ppos.html),
updated 3 September 2026. We also correct an unsupported implication in
our project's opening-16 research. **Opening 16 remains unresolved.**
No claim of a new P-position or a first independent verification is made.

Here P means losing for the player about to move, with optimal play; N
means winning. Positions are represented by the minimal generators of
their additive monoids. Move 1 loses immediately and is omitted from
the recursive lists of playable moves.

## A reproducible certificate

For S={16,26,54,60,62}, the half-position is {8,13,27,30,31}.
Its Frobenius number is 49, and it is a quiet ender. It suffices to
refute every legal even move and every odd gap of the half-position
other than 1. Other odd moves leave the half-position unchanged and
produce N positions under the
[Quiet End Theorem](https://sicherman.net/sylver/enders.html).

There are **25 even obligations and 13 exceptional odd obligations**.
The certificate covers all 38. For example, move 56 is refuted by reply
91, producing the finite P-position {16,26,54,56,60,62,91}.

The public certificate was rebuilt separately from the larger research
campaign. Its builder reads the included public project response tables
as candidate replies and recomputes finite outcomes. Missing replies are
searched in ascending odd order, without imported claim files or campaign
caches. The saved search logs record these discoveries. Previously hinted
replies are not copied from the private campaign into this reconstruction.

`evidence/certificate.json` records the dependency graph.
`CERTIFICATE.md` displays the root's response table and the exact trust
dependencies. `verify.py` independently enumerates semigroup gaps by
elementary coin reachability, checks all identities and complete covers,
rejects circular dependencies, and by default recompiles the included C++
evaluator to recompute every finite leaf. It also runs the small
periodicity control used in the correction below.

The certificate relies on the Quiet End Theorem and the explicitly listed
published P-position dependencies. The latter are distinguished from
freshly computed finite leaves. This is a computational certificate with
named mathematical dependencies, not a proof-assistant formalization.

## Correction to the opening-16 reduction

Write U={16,26,88}, X={16,26,82,88}, and Q={16,26,88,98}.
The project's previously checked branches of U leave X and Q as the
two residual obligations. Consequently the correct reduction is

```
U is P  iff  X is N and Q is N.
U is N  iff  X is P or  Q is P.
```

Because 98=16+82, adding 82 to Q gives X. Therefore X P implies Q N.
It does not imply that X N forces Q N. The earlier assertion
“U is N iff X is P” was unsupported.

An explicit counterexample to that absorption inference starts at {8,10}.
Move 4 gives {4,10}, an N-position via reply 6 to {4,6}.
Move 22 gives the established P-position {8,10,22}. Adding 4 to this
latter position again gives {4,10}, since 22=4+8+10. Thus the same
absorption relation can coexist with opposite outcomes for the two
children. The included periodicity engine detects a full-state period
of length 8 starting at odd 49 for the odd children of {8,10,22}; all
are N. Its even children have explicit replies to {2,3}, {4,6}, and
the published pairing position {8,10,12,14}.

The bundle checks these identities and counterexample controls. It does
not repackage the entire historical U branch audit. The residual
biconditionals above use that prior branch work as their premise.

## What remains

The larger bounded campaign assembled 33 short P certificates, including
previously known positions. That count describes the internal campaign;
this public bundle contains the dependency closure for the one position
certified above. Private source documents and their derived records are
not included, and the full corpus audit is not a reproducibility claim
for this release.

X's even side is refuted, but its infinite odd side remains unresolved;
the first unverified odd child in the project's scan is 409. Q also
remains unresolved. A possible route to Q N is W={16,26,62,98}, since
Q+62=W. W's odd obligations are complete; its remaining even moves are
66,70,72,86,92,102,108,118,134. These frontier figures summarize the
project's campaign, rather than additional certificates in this bundle.

The practical consequence of the correction is that an odd P hit below X
would prove X N, but a separate Q N proof would still be needed to certify
U P. Improving the periodicity engine and resolving W's remaining even
children are the next research directions.
