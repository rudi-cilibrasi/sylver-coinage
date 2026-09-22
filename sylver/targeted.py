"""Evaluate individual odd children without constructing a periodicity row.

The translated recurrence is unchanged. Instead of an eager scan making all
earlier singleton outcomes available, each query establishes exactly the
prefix needed by its reset cutoff. No complete automaton state is claimed.
"""

from sylver.periodicity import PeriodicityEngine


class TargetedEngine(PeriodicityEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_to = {}

    def _ensure_single_history(self, ekey):
        # The eager engine calls this for each newly encountered even part.
        # In this engine _has_winning_move supplies the required history at
        # the child's actual anchor, including for already-known even parts.
        pass

    def _ensure_reset_history(self, ekey, cutoff):
        if self._flag(ekey, cutoff):
            return
        self._register_shape(ekey, (0,))
        for n in range(self.history_to.get(ekey, 1) + 2, cutoff + 1, 2):
            result = self._evaluate(ekey, (0,), n)
            self.history_to[ekey] = n
            if result:
                return  # An existential reset witness suffices.

    def _has_winning_move(self, ekey, offsets, m, anchors):
        # This cutoff is strictly smaller than m, so history reconstruction
        # cannot recursively demand the very singleton it is reconstructing.
        self._ensure_reset_history(ekey, m - self.tbar - 2)
        return super()._has_winning_move(ekey, offsets, m, anchors)

    def outcome_single(self, n):
        if type(n) is not int or n < 3 or n % 2 == 0:
            raise ValueError("the target must be an odd integer at least 3")
        return self._evaluate(frozenset(), (0,), n)

    def step(self):
        raise RuntimeError("targeted evaluation does not maintain complete rows")

    def snapshot(self):
        raise RuntimeError("targeted evaluation cannot certify periodicity")
