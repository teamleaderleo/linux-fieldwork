from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterTransformSemanticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.patch = cls.repo / (
            "investigations/tarfilter-transform-semantics/"
            "tarfilter-gnu-transform-semantics.patch"
        )
        if shutil.which("tar") is None or shutil.which("patch") is None:
            raise unittest.SkipTest("GNU tar and patch are required")

    @staticmethod
    def input_archive() -> bytes:
        output = io.BytesIO()
        content = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            member = tarfile.TarInfo("a/a")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        return output.getvalue()

    @staticmethod
    def archive_names(data: bytes) -> list[str]:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            return [member.name for member in archive]

    def run_filter(
        self, tarfilter: pathlib.Path, expression: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(tarfilter), "--transform", expression],
            input=self.input_archive(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @staticmethod
    def gnu_tar_name(expression: str, work: pathlib.Path) -> str:
        root = work / "gnu-root"
        archive_path = work / "gnu.tar"
        (root / "a").mkdir(parents=True)
        (root / "a/a").write_text("payload\n")
        completed = subprocess.run(
            [
                "tar",
                "--format=pax",
                "--transform",
                expression,
                "-cf",
                str(archive_path),
                "-C",
                str(root),
                "a/a",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        with tarfile.open(archive_path, "r:*") as archive:
            names = [member.name for member in archive]
        if len(names) != 1:
            raise AssertionError(names)
        return names[0]

    def test_candidate_matches_gnu_substitution_and_flag_semantics(self) -> None:
        negative = self.run_filter(self.source, "s/a/b/")
        self.assertEqual(negative.returncode, 0, negative.stderr.decode())
        self.assertEqual(self.archive_names(negative.stdout), ["b/b"])
        rejected_global = self.run_filter(self.source, "s/a/b/g")
        self.assertNotEqual(rejected_global.returncode, 0)

        with tempfile.TemporaryDirectory(prefix="tarfilter-transform-") as td:
            work = pathlib.Path(td)
            candidate_repo = work / "candidate"
            candidate_source = candidate_repo / "upstream/mmdebstrap/tarfilter"
            candidate_source.parent.mkdir(parents=True)
            shutil.copy2(self.source, candidate_source)
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate_repo), "-i", str(self.patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            cases = {
                "s/a/b/": "b/a",
                "s/a/b/g": "b/b",
                "s/A/b/i": "b/a",
                "s/A/b/gi": "b/b",
                "s/A/b/ig": "b/b",
                "s/a/[&]/": "[a]/a",
                r"s/a/\&/": "&/a",
                r"s#a#x\#y#": "x#y/a",
                r"s#a#\\#": "\\/a",
            }
            for expression, expected in cases.items():
                with self.subTest(expression=expression):
                    completed = self.run_filter(candidate_source, expression)
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", "replace"),
                    )
                    self.assertEqual(self.archive_names(completed.stdout), [expected])
                    self.assertEqual(
                        self.gnu_tar_name(expression, work / expression.encode().hex()),
                        expected,
                    )

            for expression, message in (
                ("s/a/b/gg", "duplicate transform flags"),
                ("s/a/b/ii", "duplicate transform flags"),
                ("s/a/b/x", "unsupported transform flags"),
                ("s/a/b/gix", "unsupported transform flags"),
            ):
                with self.subTest(invalid_expression=expression):
                    completed = self.run_filter(candidate_source, expression)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(message, completed.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
