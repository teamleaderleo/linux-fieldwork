import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "mmdebstrap" / "tests" / "dev-ptmx"
PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-dev-ptmx-bsdutils"
    / "0001-include-bsdutils.patch"
)
EVIDENCE = (
    ROOT
    / "investigations"
    / "mmdebstrap-dev-ptmx-bsdutils"
    / "debci-72574145-summary.json"
)


def include_line(text):
    return next(line for line in text.splitlines() if "--include=" in line)


def inner_script_hooks(text):
    return [
        line.strip()
        for line in text.splitlines()
        if "--customize-hook=" in line and "script -c" in line
    ]


class MmdebstrapDevPtmxDependencyTests(unittest.TestCase):
    def apply_candidate(self):
        tempdir = tempfile.TemporaryDirectory(prefix="mmdebstrap-dev-ptmx-")
        self.addCleanup(tempdir.cleanup)
        tree = pathlib.Path(tempdir.name) / "tree"
        destination = tree / "upstream" / "mmdebstrap" / "tests"
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
        return (destination / "dev-ptmx").read_text(encoding="utf-8")

    def test_baseline_uses_script_inside_root_without_bsdutils(self):
        baseline = SOURCE.read_text(encoding="utf-8")

        self.assertEqual(len(inner_script_hooks(baseline)), 2)
        self.assertNotIn("bsdutils", include_line(baseline))

    def test_candidate_adds_provider_to_generated_root(self):
        candidate = self.apply_candidate()

        self.assertIn(
            "--include=bsdutils,gcc,libc6-dev,python3,passwd",
            include_line(candidate),
        )
        self.assertEqual(len(inner_script_hooks(candidate)), 2)

    def test_candidate_changes_only_the_include_line(self):
        baseline_lines = SOURCE.read_text(encoding="utf-8").splitlines()
        candidate_lines = self.apply_candidate().splitlines()
        self.assertEqual(len(baseline_lines), len(candidate_lines))

        differences = [
            (index + 1, before, after)
            for index, (before, after) in enumerate(zip(baseline_lines, candidate_lines))
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

    def test_hook_order_is_unchanged(self):
        baseline = SOURCE.read_text(encoding="utf-8")
        candidate = self.apply_candidate()

        baseline_hooks = [
            line for line in baseline.splitlines() if "--customize-hook=" in line
        ]
        candidate_hooks = [
            line for line in candidate.splitlines() if "--customize-hook=" in line
        ]
        self.assertEqual(candidate_hooks, baseline_hooks)

    def test_historical_evidence_names_the_missing_provider(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

        self.assertEqual(evidence["run_id"], 72574145)
        self.assertEqual(evidence["trigger"], "migration-reference%2F0")
        self.assertEqual(evidence["failure"]["name"], "dev-ptmx")
        self.assertEqual(evidence["failure"]["mode"], "root")
        self.assertEqual(evidence["failure"]["variant"], "apt")
        self.assertEqual(evidence["command_provider"]["package"], "bsdutils")
        self.assertEqual(evidence["command_provider"]["path"], "/usr/bin/script")
        self.assertNotIn(
            "bsdutils", evidence["generated_root_include_before_fix"]
        )
        self.assertIn("script", evidence["failure"]["message"])


if __name__ == "__main__":
    unittest.main()
