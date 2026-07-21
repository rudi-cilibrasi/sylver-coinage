"""Finite certificate edges for the proposed P-position ``{16,20,28}``."""

from __future__ import annotations

from math import gcd

from sylver.short_certificates import (
    is_generated,
    minimal_generators,
    verify_published_short_certificates,
)
from sylver.solver import solve_position


G4_CANDIDATE = (16, 20, 28)

# Opponent move, response, destination kind.  ``C`` is the already certified
# gcd-two P-position {4,6}; every other destination has gcd one and is solved
# directly by the exact finite evaluator.
G4_CANDIDATE_EVEN_RESPONSES = (
    (2, 3, "finite"),
    (4, 6, "C"),
    (6, 4, "C"),
    (8, 26, "G"),
    (10, 9, "finite"),
    (14, 31, "finite"),
    (18, 5, "finite"),
    (22, 29, "finite"),
    (24, 5, "finite"),
    (26, 38, "J"),
    (30, 29, "finite"),
    (34, 22, "L"),
    (38, 26, "J"),
    (42, 30, "N"),
    (46, 35, "finite"),
    (50, 38, "M"),
)


def verify_g4_candidate_even_responses() -> tuple[tuple[int, int, str], ...]:
    """Verify the currently known finite even branches of the candidate."""

    verify_published_short_certificates()
    for move, response, destination in G4_CANDIDATE_EVEN_RESPONSES:
        if is_generated(G4_CANDIDATE, move):
            raise AssertionError(f"opponent move {move} is illegal")
        child = minimal_generators((*G4_CANDIDATE, move))
        if is_generated(child, response):
            raise AssertionError(f"response {response} to {move} is illegal")
        reached = minimal_generators((*child, response))
        if destination in {"C", "G", "J", "L", "M", "N"}:
            expected = {
                "C": (4, 6),
                "G": (8, 20, 26),
                "J": (16, 20, 26, 28, 38),
                "L": (16, 20, 22, 28, 34),
                "M": (16, 20, 28, 38, 50),
                "N": (16, 20, 28, 30, 42),
            }[destination]
            if reached != expected:
                raise AssertionError(f"response reached {reached}, not {destination}")
            continue
        if gcd(*reached) != 1:
            raise AssertionError(f"finite response reached gcd {gcd(*reached)}")
        if solve_position(reached).is_winning:
            raise AssertionError(f"response {response} to {move} is not P")
    return G4_CANDIDATE_EVEN_RESPONSES
