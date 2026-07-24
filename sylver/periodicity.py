"""Ultimate-periodicity engine for gcd-two Sylver Coinage positions.

The Periodicity Theorem (Winning Ways ch. 18; Sicherman, Integers 2 (2002),
#G02) states that for a position ``S`` with ``g(S)=2`` the outcomes of
``S+x`` over odd ``x`` are eventually periodic, because the analysis is
computable by a finite-state system.  This module implements that system
exactly and certifies the period.

Structure.  Let ``h = S/2`` with Frobenius number ``f`` and ``tbar = 2f``.
Every reachable position from ``S+x`` is ``<E, A>`` where ``E`` is one of
the finitely many even overmonoids of ``S`` (an oversemigroup of ``h``,
reached by even moves) and ``A`` is a set of odd anchors.  Three exact
facts organize the game:

- an odd move ``k`` with ``a - k > tbar`` for an anchor ``a`` absorbs ``a``
  (``a-k`` is an even number above ``2f``, hence in ``E``); so a move below
  ``min(A) - tbar`` resets the position to ``<E, k>``, and the value of
  that option is the monotone flag "some odd ``k`` at most a cutoff has
  ``<E, k>`` P";
- an odd move above ``max(A) + tbar`` is illegal (absorbed by an anchor);
  so live anchors always span at most ``tbar`` and interactions happen in
  a bounded window;
- for ``min(A) >= tbar + 2`` all remaining arithmetic (even-gap replies,
  window legality, absorption) is translation invariant: it depends only
  on ``E`` and the anchor offsets.

In that translated region the simplified ``(E, A)`` representation is also
complete.  Live anchors span at most ``tbar``.  A sum of two anchors is above
every even gap of ``E``, while a sum of three anchors is above the entire odd
reply window, so no untracked multi-anchor sum can affect legality or
canonicalization.

States with ``min(A) < tbar + 2`` are solved exactly with the repository
evaluators.  The scan then advances one odd value at a time, evaluating
every discovered ``(E, offsets)`` shape eagerly, and takes a snapshot of
the full window each step.  When two snapshots match after every reset flag
has left its transient ``(False, True)`` phase, the sequence is provably
periodic from the first snapshot on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from math import gcd
from pathlib import Path

from sylver.short_certificates import minimal_generators
from sylver.solver import FiniteSolver, solve_position


def _half_semigroup_mask(generators: tuple[int, ...], bound: int) -> int:
    mask = 1
    for value in range(1, bound + 1):
        for g in generators:
            if value >= g and (mask >> (value - g)) & 1:
                mask |= 1 << value
                break
    return mask


class PeriodicityEngine:
    """Exact odd-tail analysis of one gcd-two position."""

    def __init__(
        self,
        generators: tuple[int, ...],
        native_binary: str | None = None,
        base_cache_path: str | None = None,
    ) -> None:
        base = minimal_generators(generators)
        if gcd(*base) != 2:
            raise ValueError("the engine requires a gcd-two position")
        self.base = base
        self.half = tuple(v // 2 for v in base)
        # If 2 has been played, the half-semigroup is <1> and has no positive
        # gaps.  Use the convenient window parameter f=0; FiniteSolver quite
        # properly rejects 1 as a playable generator, but no fallback state is
        # needed in this degenerate translated recurrence.
        self.f = 0 if self.half[0] == 1 else FiniteSolver(self.half).frobenius
        self.tbar = 2 * self.f
        self.auto_min = self.tbar + 2
        self.native = native_binary
        # Even part in half coordinates: membership mask up to f (every
        # half value above f is inside).  An even part is canonically the
        # frozenset of half-gaps of h that have been filled.
        self.base_mask = _half_semigroup_mask(self.half, self.f + 1)
        self.base_gaps = tuple(
            v for v in range(1, self.f + 1) if not (self.base_mask >> v) & 1
        )
        # exact-outcome cache for base-region positions, persisted
        self.base_cache_path = base_cache_path
        self.base_cache: dict[str, bool] = {}
        if base_cache_path and Path(base_cache_path).exists():
            self.base_cache = json.loads(Path(base_cache_path).read_text())
        # memo[(E, offsets)][m] = True for P, False for N
        self.memo: dict[tuple[frozenset[int], tuple[int, ...]], dict[int, bool]] = {}
        # per-E single-anchor P hits (sorted list of odd anchors with P)
        self.single_p_hits: dict[frozenset[int], list[int]] = {}
        # every discovered (E, offsets) shape, in discovery order
        self.shapes: list[tuple[frozenset[int], tuple[int, ...]]] = []
        self.shape_set: set[tuple[frozenset[int], tuple[int, ...]]] = set()
        self._register_shape(frozenset(), (0,))
        self.scanned_to = 1  # largest odd value fully evaluated

    # ----- even-part helpers -------------------------------------------------

    def _register_shape(self, ekey: frozenset[int], offsets: tuple[int, ...]) -> None:
        shape = (ekey, offsets)
        if shape not in self.shape_set:
            self.shape_set.add(shape)
            self.shapes.append(shape)
            self.memo.setdefault(shape, {})
            self.single_p_hits.setdefault(ekey, [])

    @lru_cache(maxsize=None)
    def _emask(self, ekey: frozenset[int]) -> int:
        mask = self.base_mask
        for gap in ekey:
            mask |= 1 << gap
        # close under addition of half generators and filled gaps
        changed = True
        values = self.half + tuple(sorted(ekey))
        while changed:
            changed = False
            for v in range(1, self.f + 1):
                if (mask >> v) & 1:
                    continue
                for g in values:
                    if v > g and (mask >> (v - g)) & 1:
                        mask |= 1 << v
                        changed = True
                        break
        return mask

    def _even_member(self, ekey: frozenset[int], diff: int) -> bool:
        """Is the even number ``diff`` in the even part ``E``?"""
        half = diff // 2
        if half > self.f:
            return True
        return bool((self._emask(ekey) >> half) & 1)

    def _even_gaps(self, ekey: frozenset[int]) -> tuple[int, ...]:
        mask = self._emask(ekey)
        return tuple(
            2 * v for v in range(1, self.f + 1) if not (mask >> v) & 1
        )

    def _fill(self, ekey: frozenset[int], even_gap: int) -> frozenset[int]:
        """Even part after the even move ``even_gap`` (full coordinates)."""
        mask = self._emask(ekey)
        new = set(ekey)
        new.add(even_gap // 2)
        # canonical key: all half-gaps of h that are now filled
        newmask = self.base_mask
        for gap in new:
            newmask |= 1 << gap
        values = self.half + tuple(sorted(new))
        changed = True
        while changed:
            changed = False
            for v in range(1, self.f + 1):
                if (newmask >> v) & 1:
                    continue
                for g in values:
                    if v > g and (newmask >> (v - g)) & 1:
                        newmask |= 1 << v
                        changed = True
                        break
        return frozenset(
            v
            for v in range(1, self.f + 1)
            if (newmask >> v) & 1 and not (self.base_mask >> v) & 1
        )

    def _egenerators(self, ekey: frozenset[int]) -> tuple[int, ...]:
        """Full-coordinate generators of the even part."""
        return minimal_generators(
            self.base + tuple(2 * v for v in sorted(ekey))
        ) if ekey else self.base

    # ----- anchor canonicalization ------------------------------------------

    def _canonical_anchors(
        self, ekey: frozenset[int], anchors: tuple[int, ...]
    ) -> tuple[int, ...]:
        """Remove anchors absorbed by a smaller anchor plus the even part."""
        live: list[int] = []
        for a in sorted(anchors):
            absorbed = any(self._even_member(ekey, a - b) for b in live)
            if not absorbed:
                live.append(a)
        return tuple(live)

    # ----- exact base evaluation --------------------------------------------

    def _exact_outcome(self, ekey: frozenset[int], anchors: tuple[int, ...]) -> bool:
        gens = minimal_generators(self._egenerators(ekey) + anchors)
        key = ",".join(map(str, gens))
        if key in self.base_cache:
            return self.base_cache[key]
        result: bool | None = None
        if self.native:
            try:
                proc = subprocess.run(
                    [self.native, *map(str, gens)],
                    capture_output=True,
                    text=True,
                    timeout=6000,
                )
                if proc.returncode == 0:
                    result = proc.stdout.startswith("P ")
            except (subprocess.TimeoutExpired, OSError):
                result = None
        if result is None:
            result = solve_position(gens).winning_move is None
        self.base_cache[key] = result
        if self.base_cache_path:
            Path(self.base_cache_path).write_text(json.dumps(self.base_cache))
        return result

    # ----- game evaluation in the automaton region --------------------------

    def _flag(self, ekey: frozenset[int], cutoff: int) -> bool:
        """Is some ``<E, k>`` with odd ``k <= cutoff`` a P-position?"""
        hits = self.single_p_hits.get(ekey)
        return bool(hits) and hits[0] <= cutoff

    def _ensure_single_history(self, ekey: frozenset[int]) -> None:
        """Evaluate the single-anchor sequence of a new even part up to date."""
        shape = (ekey, (0,))
        self._register_shape(ekey, (0,))
        table = self.memo[shape]
        for n in range(3, self.scanned_to + 1, 2):
            if n not in table:
                self._evaluate(ekey, (0,), n)

    def _evaluate(self, ekey: frozenset[int], offsets: tuple[int, ...], m: int) -> bool:
        """Outcome of the position with anchors ``m + offsets`` on ``E``.

        True means P.  Requires every dependency with smaller minimum
        anchor to be available (eager scan order guarantees it).
        """
        shape = (ekey, offsets)
        table = self.memo.setdefault(shape, {})
        if m in table:
            return table[m]
        anchors = tuple(m + o for o in offsets)
        if m < self.auto_min:
            result = self._exact_outcome(ekey, anchors)
        else:
            result = not self._has_winning_move(ekey, offsets, m, anchors)
        table[m] = result
        if offsets == (0,) and result:
            hits = self.single_p_hits.setdefault(ekey, [])
            if m not in hits:
                hits.append(m)
                hits.sort()
        return result

    def _has_winning_move(
        self,
        ekey: frozenset[int],
        offsets: tuple[int, ...],
        m: int,
        anchors: tuple[int, ...],
    ) -> bool:
        top = anchors[-1]
        # 1. reset moves: odd k <= m - tbar - 2 wins iff some <E,k> is P
        if self._flag(ekey, m - self.tbar - 2):
            return True
        # 2. window odd moves
        for k in range(m - self.tbar, top + self.tbar + 1, 2):
            if k == m or k in anchors or k < 3:
                continue
            if any(a < k and self._even_member(ekey, k - a) for a in anchors):
                continue  # illegal: absorbed by an anchor
            new = self._canonical_anchors(ekey, anchors + (k,))
            nmin = new[0]
            noffsets = tuple(a - nmin for a in new)
            self._register_shape(ekey, noffsets)
            child_table = self.memo[(ekey, noffsets)]
            if nmin not in child_table:
                child = self._evaluate(ekey, noffsets, nmin)
            else:
                child = child_table[nmin]
            if child:
                return True
        # 3. even moves
        for b in self._even_gaps(ekey):
            nekey = self._fill(ekey, b)
            self._ensure_single_history(nekey)
            new = self._canonical_anchors(nekey, anchors)
            nmin = new[0]
            noffsets = tuple(a - nmin for a in new)
            self._register_shape(nekey, noffsets)
            child_table = self.memo[(nekey, noffsets)]
            if nmin not in child_table:
                child = self._evaluate(nekey, noffsets, nmin)
            else:
                child = child_table[nmin]
            if child:
                return True
        return False

    # ----- the scan ----------------------------------------------------------

    def step(self) -> int:
        """Advance the scan by one odd value; return the new frontier."""
        n = self.scanned_to + 2
        # A transition may discover another shape.  Evaluate those new shapes
        # at this frontier too: a period snapshot is only a complete automaton
        # state when every registered row has a value at the frontier.
        cursor = 0
        while cursor < len(self.shapes):
            ekey, offsets = self.shapes[cursor]
            self._evaluate(ekey, offsets, n)
            cursor += 1
        self.scanned_to = n
        return n

    def outcome_single(self, n: int) -> bool:
        """Outcome (True = P) of ``base + n`` for odd ``n``; scans as needed."""
        while self.scanned_to < n:
            self.step()
        return self.memo[(frozenset(), (0,))][n]

    def snapshot(self) -> tuple:
        """Hashable full description of the current window and flags."""
        lo = self.scanned_to - self.tbar
        rows = []
        for ekey, offsets in self.shapes:
            table = self.memo[(ekey, offsets)]
            row = tuple(
                table.get(m) for m in range(lo, self.scanned_to + 1, 2)
            )
            rows.append((tuple(sorted(ekey)), offsets, row))
        flags = tuple(
            (
                tuple(sorted(ekey)),
                self._flag(ekey, lo - 2),
                self._flag(ekey, self.scanned_to),
            )
            for ekey in sorted(self.single_p_hits, key=sorted)
        )
        return (tuple(sorted(rows)), flags)

    def flags_are_stable(self) -> bool:
        """Return whether reset flags no longer have a moving boundary.

        For an even part ``E``, the two flags say whether a single-anchor
        P-position has occurred before the left edge of the recurrence window
        and anywhere through the current frontier.  ``(False, True)`` is a
        transient state: the first P-hit is still inside the window, so an
        otherwise repeated snapshot does not yet certify future repetition.
        The other two possibilities are stable under a repeated full window.
        """

        cutoff = self.scanned_to - self.tbar - 2
        return all(
            self._flag(ekey, cutoff) == self._flag(ekey, self.scanned_to)
            for ekey in self.single_p_hits
        )

    def prune(self, keep: int) -> None:
        """Drop memo entries below ``scanned_to - keep`` to bound memory."""
        cut = self.scanned_to - keep
        for table in self.memo.values():
            for m in [m for m in table if m < cut]:
                del table[m]


@dataclass(frozen=True)
class TailReport:
    """Certified description of the odd-outcome tail."""

    generators: tuple[int, ...]
    tbar: int
    p_values: tuple[int, ...]
    scanned_to: int
    period_start: int | None
    period_length: int | None

    @property
    def tail_all_n(self) -> bool:
        return self.period_start is not None and not any(
            v >= self.period_start for v in self.p_values
        )


sys.setrecursionlimit(100_000)


def analyze_odd_tail(
    generators: tuple[int, ...],
    limit: int,
    native_binary: str | None = None,
    base_cache_path: str | None = None,
    snapshot_interval: int = 2,
    prune_window: int | None = None,
) -> TailReport:
    """Scan the odd tail of a gcd-two position up to ``limit``.

    Returns the P-values found and, when two full window snapshots match
    with stable flags, the certified preperiod and period.  A matching pair
    proves that the outcome sequence repeats forever: the step function
    depends only on the complete window and reset flags, and stable flags are
    either already saturated or have no P-hit in the repeated window.
    """

    engine = PeriodicityEngine(generators, native_binary, base_cache_path)
    seen: dict[tuple, int] = {}
    period_start = period_length = None
    while engine.scanned_to < limit:
        n = engine.step()
        if prune_window:
            engine.prune(prune_window)
        if (
            n >= engine.auto_min + engine.tbar
            and n % (2 * snapshot_interval) == 1
            and engine.flags_are_stable()
        ):
            snap = engine.snapshot()
            if snap in seen:
                period_start = seen[snap]
                period_length = n - seen[snap]
                break
            seen[snap] = n
    p_values = tuple(sorted(engine.single_p_hits.get(frozenset(), [])))
    return TailReport(
        generators=engine.base,
        tbar=engine.tbar,
        p_values=p_values,
        scanned_to=engine.scanned_to,
        period_start=period_start,
        period_length=period_length,
    )
