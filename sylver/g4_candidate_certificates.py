"""Finite certificate edges for the proposed P-position ``{16,20,28}``."""

from __future__ import annotations

from math import gcd

from sylver.short_certificates import (
    is_generated,
    legal_moves_at_gcd_two,
    minimal_generators,
    verify_published_short_certificates,
)
from sylver.solver import FiniteSolver, solve_position


G4_CANDIDATE = (16, 20, 28)

# This position is too large for the Python reference evaluator to re-run in
# every unit test.  The independent native recurrence proves it P in
# tests/test_sylver_native_solver.py and RUN_G4_MOVE_66.txt.  Keeping the exact
# canonical target here makes that separately checked boundary explicit.
NATIVE_FINITE_P_POSITIONS = {
    (16, 20, 28, 66, 305),
    (16, 20, 28, 70, 277),
    (16, 20, 28, 74, 273),
    (16, 20, 28, 82, 145),
    (16, 20, 28, 86, 105),
}

# Opponent move, response, destination kind.  ``C`` is the already certified
# gcd-two P-position {4,6}; every other destination has gcd one and is solved
# by an exact finite evaluator.  The one large ``native-finite`` row is rerun
# by the separately compiled differential control.
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
    (54, 35, "finite"),
    (58, 43, "finite"),
    (62, 43, "finite"),
    (66, 305, "native-finite"),
    (70, 277, "native-finite"),
    (74, 273, "native-finite"),
    (78, 27, "finite"),
    (82, 145, "native-finite"),
    (86, 105, "native-finite"),
)


G4_MOVE_90_CHILD = minimal_generators((*G4_CANDIDATE, 90))

# Candidate even reply, opponent's refuting move, P-destination kind.  These
# are exactly the replies whose divide-by-two semigroup is a quiet ender.
G4_MOVE_90_SHORT_EVEN_REFUTATIONS = (
    (4, 6, "C"),
    (8, 26, "G"),
    (78, 27, "finite"),
    (102, 57, "finite"),
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
        if destination == "native-finite":
            if reached not in NATIVE_FINITE_P_POSITIONS:
                raise AssertionError(f"unknown native finite destination {reached}")
            if gcd(*reached) != 1:
                raise AssertionError("native finite response did not reach gcd one")
            continue
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


def verify_move_90_short_even_refutations() -> tuple[tuple[int, int, str], ...]:
    """Prove that every short even reply after move 90 is an N-position.

    This deliberately makes no claim about the other, long, gcd-two replies.
    For each short reply, the displayed opponent move reaches either an
    independently certified short P-node or an exactly evaluated finite
    P-position.
    """

    verify_published_short_certificates()
    short_replies: list[int] = []
    for response in legal_moves_at_gcd_two(G4_MOVE_90_CHILD):
        child = minimal_generators((*G4_MOVE_90_CHILD, response))
        if child[0] == 2:
            continue
        reduced = FiniteSolver(tuple(value // 2 for value in child))
        if reduced.is_quiet_ender():
            short_replies.append(response)
    claimed = tuple(response for response, _, _ in G4_MOVE_90_SHORT_EVEN_REFUTATIONS)
    if tuple(short_replies) != claimed:
        raise AssertionError("move-90 short even reply coverage mismatch")

    named_destinations = {"C": (4, 6), "G": (8, 20, 26)}
    for response, refutation, destination in G4_MOVE_90_SHORT_EVEN_REFUTATIONS:
        child = minimal_generators((*G4_MOVE_90_CHILD, response))
        if is_generated(child, refutation):
            raise AssertionError(f"illegal refutation {refutation} after {response}")
        reached = minimal_generators((*child, refutation))
        if destination in named_destinations:
            if reached != named_destinations[destination]:
                raise AssertionError(
                    f"{response},{refutation} reached {reached}, not {destination}"
                )
        elif destination == "finite":
            if solve_position(reached).is_winning:
                raise AssertionError(
                    f"{response},{refutation} did not reach a finite P-position"
                )
        else:
            raise AssertionError(f"unknown move-90 destination {destination}")
    return G4_MOVE_90_SHORT_EVEN_REFUTATIONS
