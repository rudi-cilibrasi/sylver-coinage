# Sylver Coinage after 16: research log

## Attempt 1 — 2026-07-20

### Goal

Build an independently checkable evaluator for finite Sylver positions, verify
it against published data, and reduce the opening `{16}` to its genuine
frontier before spending time on a large search.

### Exact finite evaluator

`solver.py` evaluates positions whose generators have gcd 1.  It:

1. computes the Apéry set and Frobenius number exactly;
2. represents the numerical semigroup as a bit set;
3. recursively evaluates every legal move other than the poisoned move 1;
4. memoizes positions and uses a commutative reply-pairing optimization; and
5. reports a winning move for an N-position or `P` for a losing position.

This is an outcome evaluator, not yet a compact proof-certificate generator.
The tests reproduce published small positions and the first four coprime
responses to 16.

### The important theoretical reduction

The naive hope was to find an odd `m` for which `{16,m}` is a finite
P-position.  Hutchings' theorem rules this out: every coprime two-generator
position with Frobenius number greater than 1 is an ender, hence an N-position.
Because 16 is even, every odd `m` is coprime to it.  Thus an odd response to 16
always loses and the unresolved responses are exactly the legal even integers.

For an even response `m`, let `d = gcd(16,m)`.  Since 16 is a power of two,
`d` is 2, 4, or 8 apart from the already-solved divisor replies.  Dividing
`{16,m}` by `d` gives a coprime pair and therefore a quiet ender.

The Quiet End Theorem supplies a further finite reduction for odd third moves.
An odd move already contained in the reduced numerical semigroup produces a
quiet ender and cannot win.  Only the finitely many odd gaps of that reduced
semigroup need exact checking.  `analyze_opening_16.py` performs this check.

### Reproduced results

The analyzer independently finds the published odd winning replies

| Position | Odd winning reply found |
| --- | ---: |
| `{16,6}` | 7 |
| `{16,10}` | 9 |
| `{16,18}` | 5 |

It finds no exceptional odd winning reply to `{16,14}`, consistent with the
published even replies 8 and 12.  The `{16,22}` exceptional-odd search exceeded
30 seconds and 215 MB on this implementation; the published winning reply is
the even move 12.

### Outcome

No solution to the bounty is claimed.  The useful result of this attempt is a
tested finite evaluator and a clean description of what remains: even response
families and P-position certificates at gcd 2, 4, and 8.  Merely extending the
gcd-one brute force will not settle `{16}`.

### Attempt 2 — finite certificate graph for `{12,16,22}`

The response `12` to `{16,22}` reaches the published P-position
`P0={12,16,22}`.  Dividing by two gives the quiet ender `{6,8,11}`, whose
Frobenius number is 21.  The Quiet End Theorem proves at once that every odd
move above 21 produces a quiet ender and is losing.  Only ten non-losing odd
moves below that threshold and eleven even moves remain.

`short_certificates.py` now checks this finite frontier without a heuristic
precision cutoff.  It also checks two subsidiary short P-position nodes,
`{4,6}` and `{12,16,20,22,26}`.  In total it verifies 17 exceptional odd
children and all 20 even children.  Every response reaches either an exactly
solved finite P-position or one of the named certificate nodes.

There is one explicit theorem boundary: after the even move 8 from `P0`, the
response 18 reaches `{8,12,18,22}`.  Blok's published proof gives this member
of the family `{8,12,8n+2,8n+6}` a simple infinite `(4n+1,4n+3)` pairing
strategy.  The local checker records that external edge instead of pretending
that a large finite truncation proves it.  Thus the certificate independently
checks all arithmetic branches while retaining one cited infinite pairing
lemma.

This confirms a strategically important response already in the literature;
it does not settle the opening `{16}`.  A scalable attack still needs a
parametric rule covering every even second move in the gcd 2, 4, and 8
classes.

### Sources

- George Sicherman, *The Care and Feeding of Enders*:
  <https://sicherman.net/sylver/enders.html>
- George Sicherman, published `{m,n}` outcomes:
  <https://sicherman.net/sylver/mnlist.html>
- Thomas Blok, *The 6-16 Tables* (2026):
  <https://sicherman.net/sylver/6-16Tables.pdf>
- R. Eaton, K. Herzinger, I. Pierce, and J. Thompson, *Numerical Semigroups
  and the Game of Sylver Coinage* (2020):
  <https://doi.org/10.1080/00029890.2020.1785254>
