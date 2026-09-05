import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from sylver.import_claims import extract, numbers, prose_claims
from sylver.reconcile_campaign import claim_target


class ClaimImportTests(unittest.TestCase):
    def test_headers_are_strict(self):
        self.assertEqual(numbers("{16, 26}"), (16, 26))
        self.assertEqual(numbers("{}"), ())
        for ambiguous in ("n+4", "12 or 14", "17?", "1;2"):
            with self.assertRaises(ValueError):
                numbers(ambiguous)

    def test_prose_replies_are_kept_without_changing_original_locations(self):
        # Synthetic syntax fixtures, not excerpts from unpublished sources.
        text = ('{6,10,14} moves to 53, more examples follow:\n'
                '{8,12,18}:75\n{10,14,18} (winning move 22)\n'
                '{6,10,22}:[22,\n{8,14,20}:[?\n')
        claims = list(prose_claims(text, 'test.docx'))
        self.assertEqual(len(claims), 4)
        self.assertEqual(claims[0]['location'], 'explicit:1')
        self.assertEqual({c['reply'] for c in claims}, {22, 53, 75})
        self.assertEqual(next(c for c in claims if c['reply'] == 53)['position'],
                         [6, 10, 14])

    def test_illegal_reply_is_quarantined_and_redundant_position_normalized(self):
        self.assertIsNone(claim_target({"position": [16, 26],
                                      "kind": "winning-reply", "reply": 42}))
        self.assertEqual(claim_target({"position": [12, 14, 44],
                                       "kind": "winning-reply", "reply": 16}),
                         (12, 14, 16))

    def test_table_cells_keep_coordinates_and_ambiguous_cells_are_skipped(self):
        rows = [["{16,26}", "28", "{}"], ["30", "𝓟", "17,19"],
                ["34", "?17", "X"], ["36", "17"]]
        def row_xml(row):
            return "<w:tr>" + "".join(
                f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>"
                for cell in row) + "</w:tr>"
        xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/'
               'wordprocessingml/2006/main"><w:body><w:tbl>' +
               "".join(map(row_xml, rows)) + "</w:tbl></w:body></w:document>")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "g=2").mkdir()
            with ZipFile(root / "g=2" / "example.docx", "w") as document:
                document.writestr("word/document.xml", xml)
            with patch("sylver.import_claims.subprocess.check_output", return_value=""):
                data = extract(root)
        self.assertEqual(len(data["claims"]), 3)
        self.assertEqual(data["claims"][0]["position"], [16, 26, 28, 30])
        self.assertEqual(data["claims"][0]["location"], "table:1/row:1/column:1")
        self.assertEqual(len(data["skipped"]), 2)
        self.assertIn("private", data["privacy"])


if __name__ == "__main__":
    unittest.main()
