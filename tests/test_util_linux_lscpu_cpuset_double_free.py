from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
INVESTIGATION = ROOT / "investigations/util-linux-lscpu-cpuset-double-free"
RUNNER = INVESTIGATION / "run_model.py"
PATCH = INVESTIGATION / "0001-clear-cpuset-output-after-error.patch"
MODEL = INVESTIGATION / "ownership_model.c"
FIXTURE = INVESTIGATION / "fixtures/v2.41"
EXPECTED_FIXTURE = """/*
 * Minimal source fixture retaining the exact util-linux v2.41
 * ul_path_cpuparse() error-path text needed to verify the canonical patch.
 * The upstream lib/path.c file declares its source public domain.
 */

static int ul_path_cpuparse(void)
{
\tint rc = 0;
\tvoid **set = 0;
\tvoid *buf = 0;

\trc = 0;

out:
\tif (rc)
\t\tcpuset_free(*set);
\tfree(buf);
\treturn rc;
}
"""


class UtilLinuxLscpuCpusetDoubleFreeTest(unittest.TestCase):
    def assert_exact_fixture(self, path: pathlib.Path) -> None:
        self.assertEqual(path.read_text(encoding="utf-8"), EXPECTED_FIXTURE)

    def test_baseline_and_candidate_ownership_matrix(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("baseline: duplicate cleanup detected (status 42)", result.stdout)
        self.assertIn("candidate: output cleared", result.stdout)

    def test_retained_patch_applies_to_the_exact_v241_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="util-linux-cpuset-patch-") as tmp:
            tree = pathlib.Path(tmp) / "source"
            shutil.copytree(FIXTURE, tree)
            path_c = tree / "lib/path.c"
            self.assert_exact_fixture(path_c)
            for extra in (["--dry-run"], []):
                result = subprocess.run(
                    [
                        "patch",
                        "--batch",
                        "--forward",
                        "--fuzz=0",
                        *extra,
                        "-p1",
                        "-i",
                        str(PATCH),
                    ],
                    cwd=tree,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                )
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIsNone(
                    re.search(r"\bfuzz\b", output, re.IGNORECASE),
                    output,
                )
            patched = path_c.read_text(encoding="utf-8")
            self.assertIn("cpuset_free(*set);\n\t\t*set = NULL;", patched)
            self.assertLess(
                patched.index("cpuset_free(*set);"),
                patched.index("*set = NULL;"),
            )

    def test_fixture_drift_is_rejected_before_patch_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="util-linux-cpuset-drift-") as tmp:
            tree = pathlib.Path(tmp) / "source"
            shutil.copytree(FIXTURE, tree)
            path_c = tree / "lib/path.c"
            path_c.write_text(
                "\n" + path_c.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with self.assertRaises(AssertionError):
                self.assert_exact_fixture(path_c)

    def test_retained_patch_clears_output_after_free(self) -> None:
        patch = PATCH.read_text(encoding="utf-8")
        self.assertIn("lib/path: avoid double free() for cpusets", patch)
        self.assertIn("cpuset_free(*set);", patch)
        self.assertIn("+\t\t*set = NULL;", patch)
        self.assertLess(
            patch.index("cpuset_free(*set);"), patch.index("*set = NULL;")
        )

    def test_model_preserves_the_relevant_ownership_boundary(self) -> None:
        source = MODEL.read_text(encoding="utf-8")
        self.assertIn("tracked_free(*output);", source)
        self.assertIn("#ifdef CLEAR_OUTPUT_AFTER_ERROR", source)
        self.assertIn("*output = NULL;", source)
        self.assertIn("tracked_free(node_map);", source)
        self.assertLess(
            source.index("tracked_free(*output);"),
            source.index("tracked_free(node_map);"),
        )


if __name__ == "__main__":
    unittest.main()
