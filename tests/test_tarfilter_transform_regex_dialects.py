from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterTransformRegexDialectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.base_patch = cls.repo / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        if shutil.which("tar") is None or shutil.which("patch") is None:
            raise unittest.SkipTest("GNU tar and patch are required")

    @staticmethod
    def archive(member_name: str) -> bytes:
        output = io.BytesIO()
        payload = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            member = tarfile.TarInfo(member_name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        return output.getvalue()

    @staticmethod
    def archive_name(data: bytes) -> str:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            names = [member.name for member in archive]
        if len(names) != 1:
            raise AssertionError(names)
        return names[0]

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

    def run_predecessor(
        self,
        candidate: pathlib.Path,
        member_name: str,
        expression: str,
    ) -> tuple[int, str | None, str]:
        completed = subprocess.run(
            [sys.executable, str(candidate), "--transform", expression],
            input=self.archive(member_name),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        name = self.archive_name(completed.stdout) if completed.returncode == 0 else None
        return (
            completed.returncode,
            name,
            completed.stderr.decode("utf-8", "replace"),
        )

    @staticmethod
    def run_gnu(
        work: pathlib.Path,
        member_name: str,
        expression: str,
    ) -> tuple[int, str | None, str]:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / member_name
        target.parent.mkdir(parents=True, exist_ok=True)
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
                member_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env={"LC_ALL": "C", "PATH": str(pathlib.Path("/usr/bin"))},
        )
        name = None
        if completed.returncode == 0:
            with tarfile.open(archive_path, "r:*") as archive:
                names = [member.name for member in archive]
            if len(names) != 1:
                raise AssertionError(names)
            name = names[0]
        return completed.returncode, name, completed.stderr

    def test_predecessor_activates_extended_operators_without_x(self) -> None:
        cases = (
            ("aaa", "s/a+/b/", "b", "aaa"),
            ("aaa", r"s/a\+/b/", "aaa", "b"),
            ("aaa", "s/(aa)/[&]/", "[aa]a", "aaa"),
            ("aaa", r"s/\(aa\)/[&]/", "aaa", "[aa]a"),
            ("aaa", "s/a{2}/b/", "ba", "aaa"),
            ("aaa", r"s/a\{2\}/b/", "aaa", "ba"),
            ("a^b", "s/a^b/x/", "a^b", "x"),
            ("a$b", "s/a$b/x/", "a$b", "x"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-default-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for member_name, expression, predecessor_name, gnu_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    pred_rc, pred_name, pred_err = self.run_predecessor(
                        candidate, member_name, expression
                    )
                    self.assertEqual(pred_rc, 0, pred_err)
                    self.assertEqual(pred_name, predecessor_name)

                    gnu_rc, actual_gnu_name, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), member_name, expression
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(actual_gnu_name, gnu_name)
                    self.assertNotEqual(pred_name, actual_gnu_name)

    def test_predecessor_rejects_explicit_extended_flag(self) -> None:
        cases = (
            ("aaa", "s/a+/b/x", "b"),
            ("aaa", "s/(aa)/[&]/x", "[aa]a"),
            ("aaa", "s/a{2}/b/x", "ba"),
            ("ab", "s/a|b/c/x", "cb"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-x-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for member_name, expression, gnu_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    pred_rc, pred_name, pred_err = self.run_predecessor(
                        candidate, member_name, expression
                    )
                    self.assertNotEqual(pred_rc, 0)
                    self.assertIsNone(pred_name)
                    self.assertIn("unsupported transform flags", pred_err)

                    gnu_rc, actual_gnu_name, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), member_name, expression
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(actual_gnu_name, gnu_name)

    def test_capture_and_backreference_follow_selected_dialect(self) -> None:
        cases = (
            ("aa", r"s/\(a\)\1/b/", False, None, 0, "b"),
            ("aa", r"s/(a)\1/b/", True, "b", 2, None),
            ("aa", r"s/(a)\1/b/x", False, None, 0, "b"),
            ("aa", r"s/\(a\)\1/b/x", False, None, 2, None),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-backref-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for (
                member_name,
                expression,
                predecessor_success,
                predecessor_name,
                gnu_rc_expected,
                gnu_name,
            ) in cases:
                with self.subTest(expression=expression):
                    pred_rc, actual_pred_name, _ = self.run_predecessor(
                        candidate, member_name, expression
                    )
                    self.assertEqual(pred_rc == 0, predecessor_success)
                    self.assertEqual(actual_pred_name, predecessor_name)

                    gnu_rc, actual_gnu_name, _ = self.run_gnu(
                        work / expression.encode().hex(), member_name, expression
                    )
                    self.assertEqual(gnu_rc, gnu_rc_expected)
                    self.assertEqual(actual_gnu_name, gnu_name)

    def test_shared_basic_subset_remains_a_control(self) -> None:
        cases = (
            ("aa", "s/a*/x/", "x"),
            ("ab", "s/^a/x/", "xb"),
            ("ab", "s/b$/x/", "ax"),
            ("a+", "s/[a+]/x/", "x+"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-control-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for member_name, expression, expected in cases:
                with self.subTest(member=member_name, expression=expression):
                    pred_rc, pred_name, pred_err = self.run_predecessor(
                        candidate, member_name, expression
                    )
                    self.assertEqual(pred_rc, 0, pred_err)
                    self.assertEqual(pred_name, expected)

                    gnu_rc, gnu_name, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), member_name, expression
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(gnu_name, expected)


if __name__ == "__main__":
    unittest.main()
