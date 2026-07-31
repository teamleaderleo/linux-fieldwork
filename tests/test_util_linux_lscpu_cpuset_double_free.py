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


class UtilLinuxLscpuCpusetDoubleFreeTest(unittest.TestCase):
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

    def test_retained_patch_applies_at_the_exact_v241_error_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="util-linux-cpuset-patch-") as tmp:
            tree = pathlib.Path(tmp) / "source"
            shutil.copytree(FIXTURE, tree)
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
                    re.search(r"\b(?:fuzz|offset)\b", output, re.IGNORECASE),
                    output,
                )
            patched = (tree / "lib/path.c").read_text(encoding="utf-8")
            self.assertIn("cpuset_free(*set);\n\t\t*set = NULL;", patched)
            self.assertLess(
                patched.index("cpuset_free(*set);"),
                patched.index("*set = NULL;"),
            )

    def test_offset_control_loses_even_when_patch_accepts_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="util-linux-cpuset-offset-") as tmp:
            tree = pathlib.Path(tmp) / "source"
            shutil.copytree(FIXTURE, tree)
            path_c = tree / "lib/path.c"
            source = path_c.read_text(encoding="utf-8")
            path_c.write_text("\n" + source, encoding="utf-8")
            result = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "--fuzz=0",
                    "--dry-run",
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
        self.assertRegex(output.lower(), r"\boffset\b")

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
