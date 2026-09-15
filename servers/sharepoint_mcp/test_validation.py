from __future__ import annotations

import unittest

from servers.sharepoint_mcp.src.validation import (
    require_relative_path,
    require_safe_id,
    require_text,
)


class ValidationTest(unittest.TestCase):
    def test_sharepoint_composite_site_id_is_valid(self) -> None:
        site_id = "contoso.sharepoint.com,site-collection-guid,site-guid"

        self.assertEqual(require_safe_id("site_id", site_id), site_id)

    def test_identifier_whitespace_is_rejected_instead_of_trimmed(self) -> None:
        with self.assertRaisesRegex(ValueError, "safe identifier"):
            require_safe_id("site_id", " site-id ")

    def test_text_is_returned_without_cleanup(self) -> None:
        self.assertEqual(require_text("content", " text "), " text ")

    def test_relative_path_rejects_navigation_and_empty_segments(self) -> None:
        for value in ("/file.txt", "../file.txt", "folder//file.txt"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    require_relative_path("file_path", value)


if __name__ == "__main__":
    unittest.main()
