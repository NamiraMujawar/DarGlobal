"""Tests for curated company briefs and PDF output.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import re
import tempfile
import unittest

from company_briefs import generate_pdfs


class CompanyBriefTests(unittest.TestCase):
    def test_generates_both_attributed_pdf_briefs(self):
        with tempfile.TemporaryDirectory() as output_dir:
            paths = generate_pdfs(output_dir)

            self.assertEqual(len(paths), 2)
            for path in paths:
                content = path.read_bytes()
                self.assertTrue(content.startswith(b"%PDF-1.4"))
                self.assertTrue(content.endswith(b"%%EOF\n"))
                self.assertIn(b"Namira Mujawar", content)
                xref_offset = int(
                    re.search(rb"startxref\n(\d+)\n%%EOF", content).group(1)
                )
                self.assertEqual(content[xref_offset : xref_offset + 4], b"xref")
                self.assertIn(b"/Type /Page", content)


if __name__ == "__main__":
    unittest.main()
