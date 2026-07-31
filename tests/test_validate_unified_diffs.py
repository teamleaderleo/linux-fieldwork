from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from tools.validate_unified_diffs import main, validate_text


class UnifiedDiffValidatorTest(unittest.TestCase):
    def test_valid_multifile_patch_and_no_newline_marker(self) -> None:
        patch = """\
diff --git a/a b/a
--- a/a
+++ b/a
@@ -1,2 +1,2 @@ heading
-old
+new
 context
\\ No newline at end of file
diff --git a/b b/b
--- a/b
+++ b/b
@@ -4 +4 @@
-before
+after
"""
        result = validate_text(patch)
        self.assertEqual(result.hunks, 2)
        self.assertEqual(result.findings, ())

    def test_hunk_content_that_looks_like_file_headers_is_counted(self) -> None:
        patch = """\
diff --git a/file b/file
--- a/file
+++ b/file
@@ -1 +1 @@
--- old-looking-content
+++ new-looking-content
"""
        result = validate_text(patch)
        self.assertEqual(result.hunks, 1)
        self.assertEqual(result.findings, ())

    def test_omitted_and_zero_counts_are_supported(self) -> None:
        patch = """\
diff --git a/new b/new
--- /dev/null
+++ b/new
@@ -0,0 +1,2 @@
+first
+second
diff --git a/old b/old
--- a/old
+++ /dev/null
@@ -1,2 +0,0 @@
-first
-second
diff --git a/one b/one
--- a/one
+++ b/one
@@ -7 +7 @@
-old
+new
"""
        result = validate_text(patch)
        self.assertEqual(result.hunks, 3)
        self.assertEqual(result.findings, ())

    def test_old_and_new_count_mismatch_is_rejected(self) -> None:
        patch = """\
--- a/file
+++ b/file
@@ -1,3 +1,2 @@
 one
-two
+three
"""
        result = validate_text(patch, path="broken.patch")
        self.assertEqual(len(result.findings), 1)
        self.assertIn("declared old/new 3/2, observed 2/2", result.findings[0].message)

    def test_malformed_header_is_rejected(self) -> None:
        result = validate_text(
            "--- a/file\n+++ b/file\n@@ -1,2 +1,not-a-number @@\n-old\n+new\n"
        )
        self.assertEqual(len(result.findings), 1)
        self.assertIn("malformed unified-diff hunk header", result.findings[0].message)

    def test_invalid_body_prefix_and_bare_empty_line_are_rejected(self) -> None:
        result = validate_text(
            "--- a/file\n+++ b/file\n@@ -1,1 +1,1 @@\nnot-prefixed\n\n"
        )
        messages = [finding.message for finding in result.findings]
        self.assertTrue(any("invalid hunk-body prefix" in message for message in messages))
        self.assertTrue(any("bare empty line inside hunk" in message for message in messages))
        self.assertTrue(any("hunk count mismatch" in message for message in messages))

    def test_mode_only_git_patch_is_valid(self) -> None:
        result = validate_text(
            "diff --git a/tool b/tool\nold mode 100644\nnew mode 100755\n"
        )
        self.assertEqual(result.hunks, 0)
        self.assertEqual(result.findings, ())

    def test_non_patch_text_is_rejected(self) -> None:
        result = validate_text("this is prose\n")
        self.assertEqual(len(result.findings), 1)
        self.assertIn("no unified-diff", result.findings[0].message)

    def test_cli_scans_directories_and_json_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "good.patch").write_text(
                "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n",
                encoding="utf-8",
            )
            nested = root / "nested"
            nested.mkdir()
            (nested / "bad.patch").write_text(
                "--- a/y\n+++ b/y\n@@ -1,2 +1,1 @@\n-old\n+new\n",
                encoding="utf-8",
            )
            (nested / "ignored.txt").write_text("not a patch", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(["--json", str(root)])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 1)
        self.assertIs(type(payload["schema_version"]), int)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["files_checked"], 2)
        self.assertEqual(payload["hunks_checked"], 2)
        self.assertEqual(len(payload["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
