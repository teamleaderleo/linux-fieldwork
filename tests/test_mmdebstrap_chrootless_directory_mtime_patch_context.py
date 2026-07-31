from __future__ import annotations

import pathlib
import re
import subprocess
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = REPOSITORY_ROOT / "upstream/mmdebstrap/mmdebstrap"
PATCH = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime"
    / "0001-normalize-root-chrootless-directory-mtimes.patch"
)
HUNK = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: .*)?$"
)


def old_hunk_slices() -> list[tuple[int, int, list[str]]]:
    lines = PATCH.read_text(encoding="utf-8").splitlines()
    result: list[tuple[int, int, list[str]]] = []
    index = 0
    while index < len(lines):
        match = HUNK.fullmatch(lines[index])
        if match is None:
            index += 1
            continue
        old_start = int(match.group("old_start"))
        old_count = int(match.group("old_count") or "1")
        old_lines: list[str] = []
        index += 1
        while index < len(lines) and not lines[index].startswith("@@"):
            line = lines[index]
            if line.startswith("diff --git "):
                break
            if line.startswith((" ", "-")):
                old_lines.append(line[1:])
            elif line.startswith("+"):
                pass
            elif line == r"\ No newline at end of file":
                pass
            else:
                raise AssertionError(
                    f"unexpected patch body at line {index + 1}: {line!r}"
                )
            index += 1
        result.append((old_start, old_count, old_lines))
    return result


class ChrootlessDirectoryMtimePatchContextTest(unittest.TestCase):
    def test_each_declared_old_slice_matches_the_exact_source(self) -> None:
        source_lines = SOURCE.read_text(encoding="utf-8").splitlines()
        hunks = old_hunk_slices()
        self.assertEqual(len(hunks), 2)
        for old_start, old_count, expected in hunks:
            with self.subTest(old_start=old_start):
                self.assertEqual(len(expected), old_count)
                actual = source_lines[old_start - 1 : old_start - 1 + old_count]
                self.assertEqual(
                    actual,
                    expected,
                    "exact old-side context differs at declared source range",
                )

    def test_git_apply_accepts_the_exact_patch(self) -> None:
        completed = subprocess.run(
            ["git", "apply", "--check", "--verbose", str(PATCH)],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_patch_dry_run_accepts_zero_fuzz_and_zero_offset(self) -> None:
        completed = subprocess.run(
            [
                "patch",
                "--dry-run",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(PATCH),
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertNotIn("fuzz", output.lower())
        self.assertNotIn("offset", output.lower())


if __name__ == "__main__":
    unittest.main()
