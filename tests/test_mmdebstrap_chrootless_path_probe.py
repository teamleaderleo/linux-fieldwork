from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


class MmdebstrapChrootlessPathProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.probe = (
            cls.repo
            / "investigations/mmdebstrap-chrootless-env/path_precedence_probe.sh"
        )

    def check_parent(self, path: pathlib.Path | str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.probe), "--check-runtime-parent", str(path)],
            cwd=self.repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_accepts_explicit_disposable_roots(self) -> None:
        for path in ("/tmp", "/var/tmp", "/home/runner/work/_temp"):
            with self.subTest(path=path):
                completed = self.check_parent(path)
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_rejects_root_repository_and_home(self) -> None:
        for path in ("/", self.repo, pathlib.Path.home()):
            with self.subTest(path=path):
                completed = self.check_parent(path)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("unsafe runtime parent", completed.stderr)

    def test_rejects_parent_component_collapse_outside_disposable_roots(self) -> None:
        completed = self.check_parent("/tmp/../etc")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("unsafe runtime parent: /etc", completed.stderr)

    def test_accepts_disposable_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            completed = self.check_parent(td)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_probe_does_not_chmod_repository_source(self) -> None:
        source = self.probe.read_text()
        self.assertNotIn('chmod 0755 "$source_root/mmdebstrap"', source)
        self.assertIn('cp --preserve=mode "$source_root/mmdebstrap"', source)
        self.assertIn("git diff --exit-code -- upstream/mmdebstrap/mmdebstrap", source)


if __name__ == "__main__":
    unittest.main()
