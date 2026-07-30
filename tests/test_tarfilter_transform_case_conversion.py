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


Snapshot = dict[str, tuple[str, str]]


class TarfilterTransformCaseConversionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.base_patch = cls.repo / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        for command in ("tar", "patch", "sed"):
            if shutil.which(command) is None:
                raise unittest.SkipTest(f"{command} is required")
        sed_version = subprocess.run(
            ["sed", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if sed_version.returncode != 0 or "GNU sed" not in sed_version.stdout:
            raise unittest.SkipTest("GNU sed is required")

    @staticmethod
    def single_archive(name: str = "AbC-def") -> bytes:
        output = io.BytesIO()
        payload = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        return output.getvalue()

    @staticmethod
    def link_archive() -> bytes:
        output = io.BytesIO()
        payload = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            target = tarfile.TarInfo("AbC-def")
            target.size = len(payload)
            archive.addfile(target, io.BytesIO(payload))

            hard = tarfile.TarInfo("AbC-hard")
            hard.type = tarfile.LNKTYPE
            hard.linkname = "AbC-def"
            archive.addfile(hard)

            sym = tarfile.TarInfo("sym")
            sym.type = tarfile.SYMTYPE
            sym.linkname = "AbC-def"
            archive.addfile(sym)
        return output.getvalue()

    @staticmethod
    def snapshot(data: bytes) -> Snapshot:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            result: Snapshot = {}
            for member in archive:
                if member.islnk():
                    kind = "hard"
                elif member.issym():
                    kind = "sym"
                else:
                    kind = "file"
                result[member.name] = (kind, member.linkname)
        return result

    def prepare_predecessor(self, work: pathlib.Path) -> pathlib.Path:
        candidate_repo = work / "candidate"
        candidate = candidate_repo / "upstream/mmdebstrap/tarfilter"
        candidate.parent.mkdir(parents=True)
        shutil.copy2(self.source, candidate)
        applied = subprocess.run(
            ["patch", "-p1", "-d", str(candidate_repo), "-i", str(self.base_patch)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        return candidate

    @staticmethod
    def run_predecessor(
        candidate: pathlib.Path,
        archive: bytes,
        expression: str,
    ) -> tuple[int, Snapshot | None, str]:
        completed = subprocess.run(
            [sys.executable, str(candidate), "--transform", expression],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = (
            TarfilterTransformCaseConversionTest.snapshot(completed.stdout)
            if completed.returncode == 0
            else None
        )
        return (
            completed.returncode,
            result,
            completed.stderr.decode("utf-8", "replace"),
        )

    @staticmethod
    def run_gnu_single(
        work: pathlib.Path,
        expression: str,
        name: str = "AbC-def",
    ) -> tuple[int, Snapshot | None, str]:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / name
        target.parent.mkdir(parents=True)
        target.write_text("payload\n")
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
                name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env={"LC_ALL": "C", "PATH": "/usr/bin"},
        )
        result = None
        if completed.returncode == 0:
            result = TarfilterTransformCaseConversionTest.snapshot(
                archive_path.read_bytes()
            )
        return completed.returncode, result, completed.stderr

    @staticmethod
    def run_gnu_links(
        work: pathlib.Path,
        expression: str,
    ) -> tuple[int, Snapshot | None, str]:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / "AbC-def"
        root.mkdir(parents=True)
        target.write_text("payload\n")
        os.link(target, root / "AbC-hard")
        os.symlink("AbC-def", root / "sym")
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
                "AbC-def",
                "AbC-hard",
                "sym",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env={"LC_ALL": "C", "PATH": "/usr/bin"},
        )
        result = None
        if completed.returncode == 0:
            result = TarfilterTransformCaseConversionTest.snapshot(
                archive_path.read_bytes()
            )
        return completed.returncode, result, completed.stderr

    @staticmethod
    def run_gnu_sed(text: str, expression: str) -> str:
        completed = subprocess.run(
            ["sed", "-E", expression],
            input=text + "\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={"LC_ALL": "C", "PATH": "/usr/bin"},
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        return completed.stdout.rstrip("\n")

    def test_predecessor_emits_case_control_letters_literally(self) -> None:
        cases = (
            (r"s/AbC/\L&/", "LAbC-def", "abc-def"),
            (r"s/AbC/\U&/", "UAbC-def", "ABC-def"),
            (r"s/AbC/\l&/", "lAbC-def", "abC-def"),
            (r"s/AbC/\u&/", "uAbC-def", "AbC-def"),
            (r"s/AbC/\E&/", "EAbC-def", "AbC-def"),
            (r"s/.*/\Uab\Lcd\Eef/", "UabLcdEef", "ABcdef"),
            (
                r"s/.*/pre\L&\Epost/",
                "preLAbC-defEpost",
                "preabc-defpost",
            ),
            (r"s/.*/\Lx\Uy\Ez/", "LxUyEz", "xYz"),
            (r"s/[a-z]/\u&/g", "AubC-udueuf", "ABC-DEF"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-case-control-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for expression, predecessor_name, gnu_name in cases:
                with self.subTest(expression=expression):
                    pred_rc, pred_result, pred_err = self.run_predecessor(
                        candidate, self.single_archive(), expression
                    )
                    self.assertEqual(pred_rc, 0, pred_err)
                    self.assertEqual(pred_result, {predecessor_name: ("file", "")})

                    gnu_rc, gnu_result, gnu_err = self.run_gnu_single(
                        work / expression.encode().hex(), expression
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(gnu_result, {gnu_name: ("file", "")})
                    self.assertNotEqual(pred_result, gnu_result)

    def test_literal_escaped_backslash_remains_a_shared_control(self) -> None:
        expression = r"s/.*/\\L&/"
        expected = {r"\LAbC-def": ("file", "")}
        with tempfile.TemporaryDirectory(prefix="tarfilter-case-literal-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            pred_rc, pred_result, pred_err = self.run_predecessor(
                candidate, self.single_archive(), expression
            )
            self.assertEqual(pred_rc, 0, pred_err)
            self.assertEqual(pred_result, expected)

            gnu_rc, gnu_result, gnu_err = self.run_gnu_single(
                work / "gnu", expression
            )
            self.assertEqual(gnu_rc, 0, gnu_err)
            self.assertEqual(gnu_result, expected)

    def test_case_controls_apply_to_member_and_link_target_fields(self) -> None:
        expression = r"s/AbC/\L&/"
        predecessor_expected: Snapshot = {
            "LAbC-def": ("file", ""),
            "LAbC-hard": ("hard", "LAbC-def"),
            "sym": ("sym", "LAbC-def"),
        }
        gnu_expected: Snapshot = {
            "abc-def": ("file", ""),
            "abc-hard": ("hard", "abc-def"),
            "sym": ("sym", "abc-def"),
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-case-links-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            pred_rc, pred_result, pred_err = self.run_predecessor(
                candidate, self.link_archive(), expression
            )
            self.assertEqual(pred_rc, 0, pred_err)
            self.assertEqual(pred_result, predecessor_expected)

            gnu_rc, gnu_result, gnu_err = self.run_gnu_links(
                work / "gnu", expression
            )
            self.assertEqual(gnu_rc, 0, gnu_err)
            self.assertEqual(gnu_result, gnu_expected)

    def test_gnu_sed_empty_capture_preserves_pending_one_shot_state(self) -> None:
        cases = (
            ("a-", r"s/(b?)-/x\u\1y/", "axY"),
            ("a-", r"s/(b?)-/x\u\1\Ey/", "axy"),
            ("a-", r"s/(b?)-/x\l\1Y/", "axy"),
            ("a-", r"s/(b)?-/x\u\1y/", "axY"),
            ("b-", r"s/(b?)-/x\u\1y/", "xBy"),
        )
        for text, expression, expected in cases:
            with self.subTest(text=text, expression=expression):
                self.assertEqual(self.run_gnu_sed(text, expression), expected)


if __name__ == "__main__":
    unittest.main()
