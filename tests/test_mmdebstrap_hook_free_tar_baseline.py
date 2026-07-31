from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools.reorder_mmdebstrap_hook_free_phase import (
    BROAD_MARKER,
    HOOK_MARKER,
    reorder_hook_free_phase,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap"
PATCH = ROOT / (
    "investigations/mmdebstrap-root-without-cap-sys-admin-hard-failure/"
    "0001-run-hook-free-capability-case-as-hard-failure.patch"
)


class HookFreeTarBaselineTest(unittest.TestCase):
    def prepare_candidate(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "candidate"
        for relative in (
            "coverage.txt",
            "coverage.py",
            "debian/tests/testsuite",
        ):
            source = SOURCE / relative
            destination = tree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(PATCH),
            ],
            cwd=tree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertNotRegex(applied.stdout + applied.stderr, r"(?i)fuzz|offset")
        return tree

    def test_target_consumes_baseline_created_by_create_directory(self) -> None:
        producer = (SOURCE / "tests/create-directory").read_text(encoding="utf-8")
        consumer = (SOURCE / "tests/root-without-cap-sys-admin").read_text(
            encoding="utf-8"
        )
        self.assertIn(">tar1.txt", producer)
        self.assertIn("diff -u tar1.txt -", consumer)

    def test_hard_phase_seeds_baseline_before_selected_capability_case(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hook-free-tar-baseline-") as td:
            tree = self.prepare_candidate(pathlib.Path(td))
            testsuite_path = tree / "debian/tests/testsuite"
            patched = testsuite_path.read_text(encoding="utf-8")
            reordered = reorder_hook_free_phase(patched).text

        prefix = 'HOOK_FREE_HARD_TESTS="create-directory $HOOK_FREE_HARD_TESTS"'
        invocation = '"$SRC/coverage.py" --exitfirst $HOOK_FREE_HARD_TESTS'
        self.assertEqual(reordered.count(prefix), 1)
        self.assertEqual(reordered.count(invocation), 1)
        self.assertLess(reordered.index(HOOK_MARKER), reordered.index(prefix))
        self.assertLess(reordered.index(prefix), reordered.index(invocation))
        self.assertLess(reordered.index(invocation), reordered.index(BROAD_MARKER))

    def test_fixture_failure_remains_authoritative(self) -> None:
        patch = PATCH.read_text(encoding="utf-8")
        self.assertIn('HOOK_FREE_HARD_TESTS="create-directory $HOOK_FREE_HARD_TESTS"', patch)
        self.assertIn('elif [ "$ret" -ne 0 ]; then', patch)
        self.assertIn('exit "$ret"', patch)
        self.assertNotIn("exit 77\n+fi\n+\n+# subtract", patch)


if __name__ == "__main__":
    unittest.main()
