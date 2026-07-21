"""Exact arithmetic interface for Blok's infinite gcd-two pairing family.

The mathematical pairing theorem is documented in ``RESEARCH.md``.  This
module checks that a concrete position has precisely the required form and
computes the prescribed reply.  It does not replace the infinite theorem by a
finite cutoff.
"""

from __future__ import annotations

from dataclasses import dataclass

from sylver.short_certificates import (
    is_generated,
    legal_moves_at_gcd_two,
    minimal_generators,
)


@dataclass(frozen=True)
class PairingFamily:
    """One position ``{8,12,8k+2,8k+6}`` and its finite even pairs."""

    parameter: int
    generators: tuple[int, ...]
    even_pairs: tuple[tuple[int, int], ...]


def pairing_family(parameter: int) -> PairingFamily:
    """Construct and exactly check the member indexed by ``parameter >= 1``."""

    if not isinstance(parameter, int) or isinstance(parameter, bool) or parameter < 1:
        raise ValueError("parameter must be a positive integer")
    generators = minimal_generators(
        (8, 12, 8 * parameter + 2, 8 * parameter + 6)
    )
    expected = tuple(sorted((8, 12, 8 * parameter + 2, 8 * parameter + 6)))
    if generators != expected:
        raise AssertionError("pairing-family member is not minimally generated")

    # The legal even move 2 is paired with the odd move 3.  The remaining
    # even moves pair as 4 <-> 6 and (8j+2) <-> (8j+6), j=1,...,k-1.
    actual_even = set(legal_moves_at_gcd_two(generators))
    expected_even = {2, 4, 6}
    expected_even.update(
        value
        for index in range(1, parameter)
        for value in (8 * index + 2, 8 * index + 6)
    )
    if actual_even != expected_even:
        raise AssertionError("derived even-gap formula failed")
    return PairingFamily(
        parameter=parameter,
        generators=generators,
        even_pairs=((4, 6),)
        + tuple(
            (8 * index + 2, 8 * index + 6)
            for index in range(1, parameter)
        ),
    )


def pairing_response(parameter: int, move: int) -> int:
    """Return the published static-pairing reply to one initial legal move.

    The complete pairing is ``2 <-> 3``, ``4 <-> 6``, every odd pair
    ``4j+1 <-> 4j+3`` for ``j >= 1``, and the finite even pairs
    ``8j+2 <-> 8j+6`` for ``1 <= j < parameter``.
    """

    family = pairing_family(parameter)
    if not isinstance(move, int) or isinstance(move, bool) or move < 2:
        raise ValueError("move must be a non-losing positive integer")
    if is_generated(family.generators, move):
        raise ValueError("move is not legal in this position")

    if move == 2:
        response = 3
    elif move == 3:
        response = 2
    elif move in (4, 6):
        response = 10 - move
    elif move % 2:
        response = move + 2 if move % 4 == 1 else move - 2
    elif move % 8 == 2:
        response = move + 4
    elif move % 8 == 6:
        response = move - 4
    else:  # Defensive: the exact legality test above should make this unreachable.
        raise AssertionError("legal even move is outside the derived pairing")

    if is_generated((*family.generators, move), response):
        raise AssertionError("pairing response was made illegal by the move")
    return response


def recognize_pairing_family(generators: tuple[int, ...]) -> PairingFamily | None:
    """Return the represented family member, or ``None`` for another monoid."""

    canonical = minimal_generators(generators)
    if len(canonical) != 4 or not {8, 12} <= set(canonical):
        return None
    first, second = (value for value in canonical if value not in (8, 12))
    if first < 10 or first % 8 != 2 or second != first + 4:
        return None
    family = pairing_family((first - 2) // 8)
    return family if family.generators == canonical else None
