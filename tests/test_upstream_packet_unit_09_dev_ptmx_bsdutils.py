import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "mmdebstrap" / "tests" / "dev-ptmx"
PATCH = (
    ROOT
    / "upstream-packets"
    / "units"
    / "09-dev-ptmx-bsdutils"
    / "patches"
    / "0001-tests-include-bsdutils-for-dev-ptmx.patch"
)

BASELINE_BLOB_SHA = "ca1cde040f945fe871f904ef6a56e040b6a5c9ea"
CANDIDATE_BLOB_SHA = "fa93b4b845ff4927a72f258364bd920e8c7dc573"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def include_line(text: str) -> str:
    return next(line for line in text.splitlines() if "--include=" in line)


def customize_hooks(text: str) -> list[str]:
    return [line for line in text.splitlines() if "--customize-hook=" in line]


def inner_script_hooks(text: str) -> list[str]:
    return [line for line in customize_hooks(text) if "script -c" in line]


class Unit09DevPtmxBsdutilsPacketTests(unittest.TestCase):
    def apply_packet_patch(self) -> bytes:
        with tempfile.TemporaryDirectory(prefix="unit09-dev-ptmx-") as tempdir:
            tree = pathlib.Path(tempdir)
            destination = tree / "tests"
            destination.mkdir(parents=True)
            shutil.copy2(SOURCE, destination / "dev-ptmx")

            completed = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "-p1",
                    "-i",
                    str(PATCH),
                ],
                cwd=tree,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertNotIn("fuzz", completed.stdout.lower())
            self.assertNotIn("offset", completed.stdout.lower())
            return (destination / "dev-ptmx").read_bytes()

    def test_imported_baseline_matches_controlled_fork_base_blob(self):
        baseline = SOURCE.read_bytes()
        text = baseline.decode("utf-8")

        self.assertEqual(git_blob_sha(baseline), BASELINE_BLOB_SHA)
        self.assertEqual(
            include_line(text),
            "\t--include=gcc,libc6-dev,python3,passwd \\",
        )
        self.assertEqual(len(inner_script_hooks(text)), 2)

    def test_packet_patch_is_upstream_rooted(self):
        patch_text = PATCH.read_text(encoding="utf-8")

        self.assertIn("diff --git a/tests/dev-ptmx b/tests/dev-ptmx", patch_text)
        self.assertNotIn("a/upstream/mmdebstrap/tests/dev-ptmx", patch_text)
        self.assertEqual(patch_text.count("--include=bsdutils"), 1)

    def test_candidate_matches_controlled_fork_candidate_blob(self):
        candidate = self.apply_packet_patch()
        candidate_text = candidate.decode("utf-8")

        self.assertEqual(git_blob_sha(candidate), CANDIDATE_BLOB_SHA)
        self.assertEqual(
            include_line(candidate_text),
            "\t--include=bsdutils,gcc,libc6-dev,python3,passwd \\",
        )
        self.assertEqual(len(inner_script_hooks(candidate_text)), 2)

    def test_candidate_changes_only_include_line_and_preserves_hooks(self):
        baseline_text = SOURCE.read_text(encoding="utf-8")
        candidate_text = self.apply_packet_patch().decode("utf-8")
        baseline_lines = baseline_text.splitlines()
        candidate_lines = candidate_text.splitlines()

        self.assertEqual(len(candidate_lines), len(baseline_lines))
        differences = [
            (index + 1, before, after)
            for index, (before, after) in enumerate(
                zip(baseline_lines, candidate_lines, strict=True)
            )
            if before != after
        ]
        self.assertEqual(
            differences,
            [
                (
                    122,
                    "\t--include=gcc,libc6-dev,python3,passwd \\",
                    "\t--include=bsdutils,gcc,libc6-dev,python3,passwd \\",
                )
            ],
        )
        self.assertEqual(customize_hooks(candidate_text), customize_hooks(baseline_text))


if __name__ == "__main__":
    unittest.main()
