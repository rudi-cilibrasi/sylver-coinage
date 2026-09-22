#!/usr/bin/env python3
"""Count even extensions and odd-offset ideals; this does not classify games."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from sylver.solver import FiniteSolver


def main():
    start = time.monotonic()
    base = (16, 26, 56, 62, 66, 76)
    half = FiniteSolver(tuple(x // 2 for x in base))
    mask = half._mask
    parts = [half.initial_state]
    seen = set(parts)
    for state in parts:
        gaps = mask & ~state
        while gaps:
            bit = gaps & -gaps
            gaps ^= bit
            child = half._adjoin(state, bit.bit_length() - 1)
            if child not in seen:
                seen.add(child)
                parts.append(child)
    counts = []
    for even in parts:
        ideals = [even]
        known = {even}
        for state in ideals:
            gaps = mask & ~state
            while gaps:
                bit = gaps & -gaps
                gaps ^= bit
                # Adding an odd anchor adds its translate of the even
                # semigroup, not arbitrary multiples of this offset.
                child = state | ((even << (bit.bit_length() - 1)) & mask)
                if child not in known:
                    known.add(child)
                    ideals.append(child)
        counts.append({"even_mask": even, "odd_ideals": len(ideals)})
    print(json.dumps({"base": base, "half_frobenius": half.frobenius,
                      "even_parts": len(parts),
                      "odd_shape_upper_bound": sum(r["odd_ideals"] for r in counts),
                      "counts": counts, "elapsed_seconds": time.monotonic() - start,
                      "scope": "State-space size only; no outcome or period conclusion."}, indent=2))


if __name__ == '__main__':
    main()
