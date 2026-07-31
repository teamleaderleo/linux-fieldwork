from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = (
    REPOSITORY_ROOT
    / ".github/workflows/verify-mmdebstrap-1135727-submission.yml"
)
SOURCE_LINES = (
    "my @tempdir_options = (TMPDIR => 1);",
    "if (defined $ENV{TMPDIR} && $ENV{TMPDIR} ne '') {",
    "@tempdir_options = (DIR => $ENV{TMPDIR});",
    "$options->{root} = tempdir('mmdebstrap.XXXXXXXXXX', @tempdir_options);",
)
DOCUMENTATION = (
    "For the C<tar>, C<squashfs>, C<ext2>, C<ext4>, and C<null> formats,"
)
COVERAGE_MARKER = "Test: fail-with-unwritable-tmpdir"
TEST_MARKERS = (
    'TMPDIR="$tmpdir"',
    "grep -F 'I: using /tmp/mmdebstrap.'",
)


def extract_source_receipt() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    marker = 'python3 - "$work" <<\'PY\''
    starts = [index for index, line in enumerate(lines) if line.strip() == marker]
    if len(starts) != 1:
        raise AssertionError(
            f"expected one source-receipt heredoc marker, found {len(starts)}"
        )

    block: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line.strip() == "PY":
            break
        block.append(line)
    else:
        raise AssertionError("source-receipt heredoc terminator was not found")

    return textwrap.dedent("\n".join(block)) + "\n"


def final_diagnostic(completed: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in completed.stderr.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(
            "receipt failure did not emit a diagnostic: "
            + completed.stdout
            + completed.stderr
        )
    return lines[-1]


class SubmissionSourceReceiptTest(unittest.TestCase):
    def execute_receipt(
        self,
        *,
        optimized: bool,
        source: str | None = None,
        coverage: str | None = None,
        shell_test: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "tests").mkdir()
            (root / "mmdebstrap").write_text(
                source
                if source is not None
                else "\n".join((*SOURCE_LINES, DOCUMENTATION)) + "\n",
                encoding="utf-8",
            )
            (root / "coverage.txt").write_text(
                coverage if coverage is not None else COVERAGE_MARKER + "\n",
                encoding="utf-8",
            )
            (root / "tests/fail-with-unwritable-tmpdir").write_text(
                shell_test
                if shell_test is not None
                else "\n".join(TEST_MARKERS) + "\n",
                encoding="utf-8",
            )

            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.extend(("-", str(root)))
            return subprocess.run(
                command,
                input=extract_source_receipt(),
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

    def assert_fails_in_both_modes(
        self,
        **fixture: str,
    ) -> None:
        results = [
            self.execute_receipt(optimized=optimized, **fixture)
            for optimized in (False, True)
        ]
        for result in results:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(final_diagnostic(results[0]), final_diagnostic(results[1]))

    def test_exact_workflow_receipt_has_no_optimizer_removable_assert(self) -> None:
        tree = ast.parse(extract_source_receipt())
        assert_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertEqual(assert_nodes, [])

    def test_complete_fixture_passes_in_ordinary_and_optimized_python(self) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                completed = self.execute_receipt(optimized=optimized)
                self.assertEqual(
                    completed.returncode,
                    0,
                    completed.stdout + completed.stderr,
                )

    def test_missing_and_duplicate_source_lines_fail_in_both_modes(self) -> None:
        complete = list((*SOURCE_LINES, DOCUMENTATION))
        missing = "\n".join(line for line in complete if line != SOURCE_LINES[0]) + "\n"
        duplicate = "\n".join((*complete, SOURCE_LINES[0])) + "\n"

        for label, source in (("missing", missing), ("duplicate", duplicate)):
            with self.subTest(label=label):
                self.assert_fails_in_both_modes(source=source)

    def test_documentation_coverage_and_shell_markers_fail_in_both_modes(self) -> None:
        source_without_documentation = "\n".join(SOURCE_LINES) + "\n"
        cases = (
            {"source": source_without_documentation},
            {"coverage": ""},
            {"coverage": COVERAGE_MARKER + "\n" + COVERAGE_MARKER + "\n"},
            {"shell_test": TEST_MARKERS[1] + "\n"},
            {"shell_test": TEST_MARKERS[0] + "\n"},
        )
        for fixture in cases:
            with self.subTest(fixture=fixture):
                self.assert_fails_in_both_modes(**fixture)


if __name__ == "__main__":
    unittest.main()
