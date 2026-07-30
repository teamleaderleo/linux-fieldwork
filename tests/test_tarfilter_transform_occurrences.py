from __future__ import annotations

import io
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterTransformOccurrenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.base_patch = cls.repo / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        cls.occurrence_patch = cls.repo / (
            "investigations/tarfilter-transform-occurrence-selectors/"
            "tarfilter-transform-occurrence-selectors.patch"
        )
        if shutil.which("tar") is None or shutil.which("patch") is None:
            raise unittest.SkipTest("GNU tar and patch are required")

    @staticmethod
    def input_archive(with_links: bool = False) -> bytes:
        output = io.BytesIO()
        content = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            member = tarfile.TarInfo("a/a/a/a")
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
            if with_links:
                hard = tarfile.TarInfo("hard")
                hard.type = tarfile.LNKTYPE
                hard.linkname = "a/a/a/a"
                archive.addfile(hard)

                sym = tarfile.TarInfo("sym")
                sym.type = tarfile.SYMTYPE
                sym.linkname = "a/a/a/a"
                archive.addfile(sym)
        return output.getvalue()

    @staticmethod
    def snapshot(data: bytes) -> dict[str, tuple[str, str]]:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            result: dict[str, tuple[str, str]] = {}
            for member in archive:
                if member.islnk():
                    kind = "hard"
                elif member.issym():
                    kind = "sym"
                else:
                    kind = "file"
                result[member.name] = (kind, member.linkname)
            return result

    def run_filter(
        self,
        tarfilter: pathlib.Path,
        expression: str,
        *,
        with_links: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(tarfilter), "--transform", expression],
            input=self.input_archive(with_links=with_links),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @staticmethod
    def apply_patch(candidate_repo: pathlib.Path, patch_path: pathlib.Path) -> None:
        applied = subprocess.run(
            ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            raise AssertionError(applied.stdout + applied.stderr)

    def prepare_candidate(
        self,
        work: pathlib.Path,
        *,
        include_occurrence_patch: bool,
    ) -> pathlib.Path:
        candidate_repo = work / "candidate"
        candidate_source = candidate_repo / "upstream/mmdebstrap/tarfilter"
        candidate_source.parent.mkdir(parents=True)
        shutil.copy2(self.source, candidate_source)
        self.apply_patch(candidate_repo, self.base_patch)
        if include_occurrence_patch:
            self.apply_patch(candidate_repo, self.occurrence_patch)
        return candidate_source

    @staticmethod
    def gnu_tar_archive(
        expression: str,
        work: pathlib.Path,
        *,
        with_links: bool = False,
    ) -> bytes:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / "a/a/a/a"
        target.parent.mkdir(parents=True)
        target.write_text("payload\n")
        names = ["a/a/a/a"]
        if with_links:
            os.link(target, root / "hard")
            os.symlink("a/a/a/a", root / "sym")
            names.extend(("hard", "sym"))
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
                *names,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        return archive_path.read_bytes()

    def test_predecessor_rejects_numeric_selector(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-occurrence-negative-") as td:
            candidate = self.prepare_candidate(
                pathlib.Path(td), include_occurrence_patch=False
            )
            completed = self.run_filter(candidate, "s/a/b/2")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "unsupported transform flags",
                completed.stderr.decode("utf-8", "replace"),
            )

    def test_candidate_matches_gnu_numeric_occurrence_semantics(self) -> None:
        cases = {
            "s/a/b/": "b/a/a/a",
            "s/a/b/g": "b/b/b/b",
            "s/a/b/2": "a/b/a/a",
            "s/a/b/2g": "a/b/b/b",
            "s/a/b/g2": "a/b/b/b",
            "s/a/b/0": "b/a/a/a",
            "s/a/b/0g": "b/b/b/b",
            "s/a/b/22": "a/a/a/a",
            "s/a/b/2g3": "a/a/b/b",
            "s/A/b/2i": "a/b/a/a",
            "s/A/b/i2g": "a/b/b/b",
            "s/A/b/2gi3": "a/a/b/b",
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-occurrence-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_occurrence_patch=True
            )
            for expression, expected_name in cases.items():
                with self.subTest(expression=expression):
                    completed = self.run_filter(candidate, expression)
                    self.assertEqual(
                        completed.returncode,
                        0,
                        completed.stderr.decode("utf-8", "replace"),
                    )
                    expected = {expected_name: ("file", "")}
                    self.assertEqual(self.snapshot(completed.stdout), expected)
                    reference = self.gnu_tar_archive(
                        expression, work / expression.encode().hex()
                    )
                    self.assertEqual(self.snapshot(reference), expected)

    def test_selector_is_applied_independently_to_link_targets(self) -> None:
        expression = "s/a/b/2g"
        with tempfile.TemporaryDirectory(prefix="tarfilter-occurrence-links-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_occurrence_patch=True
            )
            completed = self.run_filter(candidate, expression, with_links=True)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", "replace"),
            )
            expected = {
                "a/b/b/b": ("file", ""),
                "hard": ("hard", "a/b/b/b"),
                "sym": ("sym", "a/b/b/b"),
            }
            self.assertEqual(self.snapshot(completed.stdout), expected)
            reference = self.gnu_tar_archive(expression, work / "gnu", with_links=True)
            self.assertEqual(self.snapshot(reference), expected)


if __name__ == "__main__":
    unittest.main()
