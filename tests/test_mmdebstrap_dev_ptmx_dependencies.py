from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest


class MmdebstrapDevPtmxDependenciesTest(unittest.TestCase):
    def test_candidate_declares_bsdutils_for_inner_script_hooks(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source = repo / "upstream/mmdebstrap/tests/dev-ptmx"
        patch = (
            repo
            / "investigations/mmdebstrap-dev-ptmx-bsdutils"
            / "0001-include-bsdutils.patch"
        )
        historical = (
            repo
            / "investigations/mmdebstrap-dev-ptmx-bsdutils"
            / "historical-failure.txt"
        )

        baseline = source.read_text(encoding="utf-8")
        old_include = "\t--include=gcc,libc6-dev,python3,passwd \\\n"
        new_include = "\t--include=bsdutils,gcc,libc6-dev,python3,passwd \\\n"

        self.assertEqual(baseline.count(old_include), 1)
        self.assertNotIn("bsdutils", self._include_packages(baseline))

        baseline_hooks = self._inner_script_hooks(baseline)
        self.assertEqual(len(baseline_hooks), 2)
        self.assertTrue(all('chroot \\"\\$1\\"' in line for line in baseline_hooks))
        self.assertNotIn("runuser -u user", baseline_hooks[0])
        self.assertIn("runuser -u user", baseline_hooks[1])

        with tempfile.TemporaryDirectory(prefix="mmdebstrap-dev-ptmx-") as tmp:
            candidate_root = pathlib.Path(tmp) / "candidate"
            candidate_source = candidate_root / "upstream/mmdebstrap/tests/dev-ptmx"
            candidate_source.parent.mkdir(parents=True)
            shutil.copy2(source, candidate_source)

            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "-p1",
                    "-i",
                    str(patch),
                ],
                cwd=candidate_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            candidate = candidate_source.read_text(encoding="utf-8")

        self.assertEqual(candidate, baseline.replace(old_include, new_include, 1))
        self.assertEqual(
            self._include_packages(candidate),
            ["bsdutils", "gcc", "libc6-dev", "python3", "passwd"],
        )
        self.assertEqual(self._inner_script_hooks(candidate), baseline_hooks)

        evidence = self._read_key_values(historical)
        self.assertEqual(evidence["debci_run"], "72574145")
        self.assertEqual(evidence["case_name"], "dev-ptmx --mode=root")
        self.assertEqual(
            evidence["root_include"], "gcc,libc6-dev,python3,passwd"
        )
        self.assertEqual(evidence["missing_command"], "script")
        self.assertEqual(evidence["bsdutils_version"], "1:2.42.2-1")
        self.assertIn("No such file or directory", evidence["error"])

    def _include_packages(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if "--include=" in line]
        self.assertEqual(lines.__len__(), 1)
        value = lines[0].split("--include=", 1)[1].split()[0]
        return value.split(",")

    @staticmethod
    def _inner_script_hooks(text: str) -> list[str]:
        return [
            line
            for line in text.splitlines()
            if "--customize-hook=" in line and "script -c" in line
        ]

    @staticmethod
    def _read_key_values(path: pathlib.Path) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            result[key] = value
        return result


if __name__ == "__main__":
    unittest.main()
