import unittest

from verify import verify


def small_certificate():
    return {"schema": 1, "root": [4, 6], "facts": {
        "2,3": {"kind": "finite-exact", "outcome": "P", "frobenius": 1, "winning_move": None},
        "2": {"kind": "winning-reply", "outcome": "N", "move": 3, "destination": "2,3"},
        "4,6": {"kind": "short-cover", "outcome": "P", "half_frobenius": 1,
                "tail": "quiet-end-theorem", "obligations": [{"move": 2, "destination": "2"}]},
    }}


class PublicVerifierTests(unittest.TestCase):
    def test_small_complete_cover(self):
        self.assertEqual(verify(small_certificate())["outcome"], "P")

    def test_missing_obligation_is_rejected(self):
        data = small_certificate()
        data["facts"]["4,6"]["obligations"] = []
        with self.assertRaisesRegex(ValueError, "incomplete cover"):
            verify(data)

    def test_illegal_reply_is_rejected(self):
        data = small_certificate()
        data["facts"]["2"]["move"] = 4
        with self.assertRaisesRegex(ValueError, "illegal edge"):
            verify(data)

    def test_false_identity_is_rejected(self):
        data = small_certificate()
        data["facts"]["2"]["destination"] = "4,6"
        with self.assertRaisesRegex(ValueError, "false semigroup identity"):
            verify(data)

    def test_arbitrary_theorem_leaf_is_rejected(self):
        data = {"schema": 1, "root": [16, 26], "facts": {"16,26": {
            "kind": "public-theorem", "outcome": "P", "source": "https://sicherman.net/sylver/ppos.html"}}}
        with self.assertRaisesRegex(ValueError, "unsupported theorem"):
            verify(data)

    def test_callback_recomputes_finite_leaves(self):
        checked = []
        verify(small_certificate(), lambda gs, fact: checked.append((gs, fact["outcome"])))
        self.assertEqual(checked, [((2, 3), "P")])


if __name__ == "__main__":
    unittest.main()
