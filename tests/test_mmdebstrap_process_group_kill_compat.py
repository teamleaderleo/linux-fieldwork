from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class MmdebstrapProcessGroupKillCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.source = self.root / "upstream/mmdebstrap/tests/sigint-during-customize-hook"
        self.patch = (
            self.root
            / "investigations/mmdebstrap-autopkgtest-1141078"
            / "sigint-process-group-kill-sid.patch"
        )
        self.harness = self.root / "scripts/reproduce-mmdebstrap-autopkgtest.sh"
        self.original = '/bin/kill --signal INT -- "$pgid"'
        self.replacement = "/bin/dash -c 'kill -s INT -- \"$1\"' dash \"$pgid\""

    def apply_patch(self, source_text: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as temporary:
            tree = Path(temporary) / "source"
            test_path = tree / "tests" / self.source.name
            test_path.parent.mkdir(parents=True)
            test_path.write_text(source_text, encoding="utf-8")
            completed = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "-p1",
                    "-d",
                    str(tree),
                    "-i",
                    str(self.patch),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            return completed, test_path.read_text(encoding="utf-8")

    def test_patch_is_one_exact_replacement(self) -> None:
        patch_text = self.patch.read_text(encoding="utf-8")
        self.assertEqual(patch_text.count("diff --git "), 1)
        self.assertEqual(patch_text.count("@@ "), 1)
        self.assertEqual(patch_text.count("-" + self.original), 1)
        self.assertEqual(patch_text.count("+" + self.replacement), 1)

    def test_zero_fuzz_application_preserves_complete_shell_and_source(self) -> None:
        source_text = self.source.read_text(encoding="utf-8")
        self.assertEqual(source_text.count(self.original), 1)
        self.assertNotIn(self.replacement, source_text)

        completed, candidate = self.apply_patch(source_text)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        combined = (completed.stdout + completed.stderr).lower()
        self.assertNotIn("fuzz", combined)
        self.assertNotIn("offset", combined)
        self.assertNotIn(self.original, candidate)
        self.assertEqual(candidate.count(self.replacement), 1)
        self.assertEqual(self.source.read_text(encoding="utf-8"), source_text)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(candidate)
            candidate_path = Path(handle.name)
        try:
            syntax = subprocess.run(
                ["/bin/sh", "-n", str(candidate_path)],
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            candidate_path.unlink()
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_source_drift_and_second_application_fail_closed(self) -> None:
        source_text = self.source.read_text(encoding="utf-8")
        drifted = source_text.replace(self.original, "/bin/kill -INT -- \"$pgid\"")
        drift_result, drift_candidate = self.apply_patch(drifted)
        self.assertNotEqual(drift_result.returncode, 0)
        self.assertEqual(drift_candidate, drifted)

        first_result, first_candidate = self.apply_patch(source_text)
        self.assertEqual(first_result.returncode, 0, first_result.stderr)
        second_result, second_candidate = self.apply_patch(first_candidate)
        self.assertNotEqual(second_result.returncode, 0)
        self.assertEqual(second_candidate, first_candidate)

    def test_reproduction_harness_applies_and_records_exact_override(self) -> None:
        script = self.harness.read_text(encoding="utf-8")
        self.assertIn('signal_patch="$repo_root/investigations/mmdebstrap-autopkgtest-1141078/sigint-process-group-kill-sid.patch"', script)
        self.assertIn('if [[ ! -f $signal_patch ]]; then', script)
        self.assertIn('-i "$signal_patch"', script)
        self.assertIn('"$source_tree/tests/sigint-during-customize-hook"', script)
        self.assertIn("Integration signal override", script)
        self.assertGreaterEqual(script.count("--fuzz=0"), 4)


if __name__ == "__main__":
    unittest.main()
