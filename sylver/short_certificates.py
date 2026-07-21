"""Check finite branches of published short ``g=2`` P-position proofs.

The Quiet End Theorem reduces odd moves above the Frobenius number of the
divide-by-two semigroup to one theorem application.  The remaining odd moves
and all even moves are finite.  This module checks those finite obligations
for a small certificate graph covering several responses after opening 16.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Iterable

from sylver.solver import FiniteSolver, solve_position


def is_generated(generators: Iterable[int], value: int) -> bool:
    """Return whether ``value`` is a nonnegative combination of generators."""

    if value < 0:
        return False
    reachable = [False] * (value + 1)
    reachable[0] = True
    values = tuple(sorted(set(generators)))
    for current in range(value + 1):
        if not reachable[current]:
            continue
        for generator in values:
            if current + generator <= value:
                reachable[current + generator] = True
    return reachable[value]


def minimal_generators(generators: Iterable[int]) -> tuple[int, ...]:
    """Return the unique minimal generators of the same additive monoid."""

    result: list[int] = []
    for value in sorted(set(generators)):
        if value < 2:
            raise ValueError("generators must exceed one")
        if not is_generated(result, value):
            result.append(value)
    return tuple(result)


def legal_moves_at_gcd_two(generators: Iterable[int]) -> tuple[int, ...]:
    """Return every legal even move; odd moves form the infinite remainder."""

    position = minimal_generators(generators)
    if gcd(*position) != 2:
        raise ValueError("position must have gcd two")
    reduced = FiniteSolver(tuple(value // 2 for value in position))
    return tuple(2 * gap for gap in reduced.gaps())


@dataclass(frozen=True)
class ShortNode:
    name: str
    generators: tuple[int, ...]
    even_responses: tuple[tuple[int, int, str], ...]


@dataclass(frozen=True)
class CertificateReport:
    nodes: int
    exceptional_odd_children: int
    even_children: int
    external_pairing_edges: int
    published_long_edges: int


NODES = (
    ShortNode("C", (4, 6), ((2, 3, "finite"),)),
    ShortNode(
        "D",
        (12, 16, 20, 22, 26),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 4, "C"),
            (8, 47, "finite"),
            (10, 31, "finite"),
            (14, 13, "finite"),
            (18, 11, "finite"),
            (30, 183, "finite"),
        ),
    ),
    ShortNode(
        "P0",
        (12, 16, 22),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 4, "C"),
            # This is the one deliberately external edge.  The destination
            # has the published (4n+1,4n+3) infinite pairing strategy.
            (8, 18, "A"),
            (10, 31, "finite"),
            (14, 47, "finite"),
            (18, 15, "finite"),
            (20, 26, "D"),
            (26, 20, "D"),
            (30, 51, "finite"),
            (42, 25, "finite"),
        ),
    ),
    ShortNode(
        "E",
        (8, 14),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 4, "C"),
            (10, 19, "finite"),
            # This reaches the first member {8,10,12,14} of Blok's
            # {8,12,8n+2,8n+6} pairing family.
            (12, 10, "A1"),
            (18, 25, "finite"),
            (20, 9, "finite"),
            (26, 17, "finite"),
            (34, 27, "finite"),
        ),
    ),
    ShortNode(
        "F",
        (12, 14, 16),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 7, "finite"),
            (8, 10, "A1"),
            (10, 8, "A1"),
            (18, 27, "finite"),
            (20, 73, "finite"),
            (22, 47, "finite"),
            (34, 21, "finite"),
        ),
    ),
    ShortNode(
        "G",
        (8, 20, 26),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 4, "C"),
            # The peer-reviewed periodicity computation establishes H as P.
            (10, 22, "H"),
            # This is parameter 3 of Blok's infinite pairing family.
            (12, 30, "A3"),
            (14, 9, "finite"),
            (18, 11, "finite"),
            (22, 13, "finite"),
            (30, 49, "finite"),
            (38, 21, "finite"),
        ),
    ),
    ShortNode(
        "J",
        (16, 20, 26, 28, 38),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 7, "finite"),
            (8, 21, "finite"),
            (10, 9, "finite"),
            (12, 29, "finite"),
            (14, 43, "finite"),
            (18, 5, "finite"),
            (22, 25, "finite"),
            (24, 5, "finite"),
            (30, 23, "finite"),
            (34, 11, "finite"),
            (50, 63, "finite"),
        ),
    ),
    ShortNode(
        "L",
        (16, 20, 22, 28, 34),
        (
            (2, 3, "finite"),
            (4, 6, "C"),
            (6, 7, "finite"),
            (8, 13, "finite"),
            (10, 19, "finite"),
            (12, 39, "finite"),
            (14, 41, "finite"),
            (18, 39, "finite"),
            (24, 23, "finite"),
            (26, 11, "finite"),
            (30, 31, "finite"),
            (46, 33, "finite"),
        ),
    ),
)

EXTERNAL_NODES = {
    "A": minimal_generators((8, 12, 18, 22)),
    "A1": minimal_generators((8, 10, 12, 14)),
    "A3": minimal_generators((8, 12, 26, 30)),
}

PUBLISHED_LONG_NODES = {
    "H": minimal_generators((8, 10, 22)),
}


def _verify_finite_response(
    position: tuple[int, ...], opponent_move: int, response: int
) -> None:
    if is_generated(position, opponent_move):
        raise AssertionError(f"claimed opponent move {opponent_move} is illegal")
    child = minimal_generators((*position, opponent_move))
    if is_generated(child, response):
        raise AssertionError(f"claimed response {response} is illegal")
    result = minimal_generators((*child, response))
    if gcd(*result) != 1:
        raise AssertionError("finite response did not reach gcd one")
    if solve_position(result).is_winning:
        raise AssertionError(f"response {response} did not reach a P-position")


def verify_published_short_certificates() -> CertificateReport:
    """Verify the finite certificate graph containing the named short nodes.

    A successful return establishes every finite branch.  The mathematical
    conclusion that each node is P additionally invokes the Quiet End Theorem
    for large odd moves and the published infinite pairing strategy for node
    A; those theorem obligations are recorded, not silently replaced by a
    finite cutoff.
    """

    by_name = {node.name: node for node in NODES}
    odd_children = 0
    even_children = 0
    external_edges = 0
    published_long_edges = 0

    for node in NODES:
        position = minimal_generators(node.generators)
        if position != node.generators or gcd(*position) != 2:
            raise AssertionError(f"{node.name} is not canonical with gcd two")
        reduced = FiniteSolver(tuple(value // 2 for value in position))
        if not reduced.is_quiet_ender():
            raise AssertionError(f"{node.name}/2 is not a quiet ender")

        # Every odd move greater than this Frobenius number is handled by the
        # Quiet End Theorem.  Check every non-losing odd move below it exactly.
        for move in range(3, reduced.frobenius + 1, 2):
            child = solve_position((*position, move))
            if not child.is_winning or child.winning_move is None:
                raise AssertionError(f"odd move {move} from {node.name} is not refuted")
            _verify_finite_response(position, move, child.winning_move)
            odd_children += 1

        claimed_moves = {move for move, _, _ in node.even_responses}
        actual_moves = set(legal_moves_at_gcd_two(position))
        if claimed_moves != actual_moves:
            raise AssertionError(
                f"{node.name} even coverage mismatch: {claimed_moves ^ actual_moves}"
            )

        for move, response, destination in node.even_responses:
            if destination == "finite":
                _verify_finite_response(position, move, response)
            else:
                child = minimal_generators((*position, move))
                if is_generated(child, response):
                    raise AssertionError(f"illegal response {response} at {node.name}")
                result = minimal_generators((*child, response))
                if destination in by_name:
                    expected = by_name[destination].generators
                elif destination in EXTERNAL_NODES:
                    expected = EXTERNAL_NODES[destination]
                    # Import lazily to avoid the pairing-family module's
                    # deliberate reuse of the elementary helpers above.
                    from sylver.pairing_family import recognize_pairing_family

                    if recognize_pairing_family(expected) is None:
                        raise AssertionError("external node is not in the pairing family")
                    external_edges += 1
                elif destination in PUBLISHED_LONG_NODES:
                    expected = PUBLISHED_LONG_NODES[destination]
                    published_long_edges += 1
                else:
                    raise AssertionError(f"unknown certificate destination {destination}")
                if result != expected:
                    raise AssertionError(
                        f"{node.name}: {move},{response} reached {result}, not {expected}"
                    )
            even_children += 1

    return CertificateReport(
        len(NODES),
        odd_children,
        even_children,
        external_edges,
        published_long_edges,
    )


OPENING_16_EVEN_RESPONSES = (
    (2, 3, "finite"),
    (4, 6, "C"),
    (6, 7, "finite"),
    (8, 14, "E"),
    (10, 9, "finite"),
    (12, 14, "F"),
    (14, 8, "E"),
    (18, 5, "finite"),
    (22, 12, "P0"),
)


def verify_opening_16_even_responses() -> tuple[tuple[int, int, str], ...]:
    """Verify the currently certified even replies after opening move 16.

    Each row is ``(opponent move, response, destination)``.  A finite
    destination is solved exactly at gcd one; a named destination is one of
    the P-position nodes checked by :func:`verify_published_short_certificates`.
    This is deliberately a partial strategy, not a claim about every even
    move after 16.
    """

    verify_published_short_certificates()
    by_name = {node.name: node.generators for node in NODES}
    opening = (16,)
    for move, response, destination in OPENING_16_EVEN_RESPONSES:
        if destination == "finite":
            _verify_finite_response(opening, move, response)
            continue
        if is_generated(opening, move):
            raise AssertionError(f"opening response {move} is illegal")
        child = minimal_generators((*opening, move))
        if is_generated(child, response):
            raise AssertionError(f"reply {response} to {move} is illegal")
        reached = minimal_generators((*child, response))
        if reached != by_name[destination]:
            raise AssertionError(
                f"reply to {move} reached {reached}, not {destination}"
            )
    return OPENING_16_EVEN_RESPONSES
