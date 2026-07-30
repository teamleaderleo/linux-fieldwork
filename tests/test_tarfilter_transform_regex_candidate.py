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


class TarfilterTransformRegexCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.scope_patch = cls.repo / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        cls.occurrence_patch = cls.repo / (
            "investigations/tarfilter-transform-occurrence-selectors/"
            "tarfilter-transform-occurrence-selectors.patch"
        )
        cls.regex_patch = cls.repo / (
            "investigations/tarfilter-transform-regex-candidate/"
            "tarfilter-transform-regex-dialects.patch"
        )
        if shutil.which("tar") is None or shutil.which("patch") is None:
            raise unittest.SkipTest("GNU tar and patch are required")

    @staticmethod
    def archive(member_name: str, *, with_links: bool = False) -> bytes:
        output = io.BytesIO()
        payload = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            member = tarfile.TarInfo(member_name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
            if with_links:
                hard = tarfile.TarInfo("hard")
                hard.type = tarfile.LNKTYPE
                hard.linkname = member_name
                archive.addfile(hard)

                sym = tarfile.TarInfo("sym")
                sym.type = tarfile.SYMTYPE
                sym.linkname = member_name
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

    @staticmethod
    def apply_patch(candidate_repo: pathlib.Path, patch_path: pathlib.Path) -> None:
        completed = subprocess.run(
            ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)

    def prepare_candidate(
        self,
        work: pathlib.Path,
        *,
        include_regex_patch: bool,
    ) -> pathlib.Path:
        candidate_repo = work / "candidate"
        candidate = candidate_repo / "upstream/mmdebstrap/tarfilter"
        candidate.parent.mkdir(parents=True)
        shutil.copy2(self.source, candidate)
        self.apply_patch(candidate_repo, self.scope_patch)
        self.apply_patch(candidate_repo, self.occurrence_patch)
        if include_regex_patch:
            self.apply_patch(candidate_repo, self.regex_patch)
        return candidate

    def run_filter(
        self,
        candidate: pathlib.Path,
        member_name: str,
        expression: str,
        *,
        with_links: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        return subprocess.run(
            [sys.executable, str(candidate), "--transform", expression],
            input=self.archive(member_name, with_links=with_links),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    @staticmethod
    def run_gnu(
        work: pathlib.Path,
        member_name: str,
        expression: str,
        *,
        with_links: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / member_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("payload\n")
        names = [member_name]
        if with_links:
            os.link(target, root / "hard")
            os.symlink(member_name, root / "sym")
            names.extend(("hard", "sym"))
        env = os.environ.copy()
        env["LC_ALL"] = "C"
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
            env=env,
        )
        if completed.returncode == 0:
            completed.stdout = archive_path.read_bytes()
        return completed

    def assert_matches_gnu(
        self,
        candidate: pathlib.Path,
        work: pathlib.Path,
        member_name: str,
        expression: str,
        expected: dict[str, tuple[str, str]],
        *,
        with_links: bool = False,
    ) -> None:
        filtered = self.run_filter(
            candidate,
            member_name,
            expression,
            with_links=with_links,
        )
        self.assertEqual(
            filtered.returncode,
            0,
            filtered.stderr.decode("utf-8", "replace"),
        )
        self.assertEqual(self.snapshot(filtered.stdout), expected)

        reference = self.run_gnu(
            work,
            member_name,
            expression,
            with_links=with_links,
        )
        self.assertEqual(
            reference.returncode,
            0,
            reference.stderr.decode("utf-8", "replace"),
        )
        self.assertEqual(self.snapshot(reference.stdout), expected)

    def test_predecessor_retains_characterized_dialect_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-predecessor-") as td:
            work = pathlib.Path(td)
            predecessor = self.prepare_candidate(work, include_regex_patch=False)

            default = self.run_filter(predecessor, "aaa", "s/a+/b/")
            self.assertEqual(default.returncode, 0, default.stderr.decode())
            self.assertEqual(self.snapshot(default.stdout), {"b": ("file", "")})

            extended = self.run_filter(predecessor, "aaa", "s/a+/b/x")
            self.assertNotEqual(extended.returncode, 0)
            self.assertIn(
                "unsupported transform flags",
                extended.stderr.decode("utf-8", "replace"),
            )

            basic_group = self.run_filter(predecessor, "aa", r"s/\(a\)\1/b/")
            self.assertNotEqual(basic_group.returncode, 0)

    def test_candidate_matches_default_and_extended_operator_matrix(self) -> None:
        cases = (
            ("aaa", "s/a+/b/", "aaa"),
            ("aaa", r"s/a\+/b/", "b"),
            ("aaa", "s/a+/b/x", "b"),
            ("aaa", r"s/a\+/b/x", "aaa"),
            ("aa", "s/a?/b/", "aa"),
            ("aa", r"s/a\?/b/", "ba"),
            ("aa", "s/a?/b/x", "ba"),
            ("aa", r"s/a\?/b/x", "aa"),
            ("ab", "s/a|b/c/", "ab"),
            ("ab", r"s/a\|b/c/", "cb"),
            ("ab", "s/a|b/c/x", "cb"),
            ("ab", r"s/a\|b/c/x", "ab"),
            ("aaa", "s/(aa)/[&]/", "aaa"),
            ("aaa", r"s/\(aa\)/[&]/", "[aa]a"),
            ("aaa", "s/(aa)/[&]/x", "[aa]a"),
            ("aaa", r"s/\(aa\)/[&]/x", "aaa"),
            ("aaa", "s/a{2}/b/", "aaa"),
            ("aaa", r"s/a\{2\}/b/", "ba"),
            ("aaa", "s/a{2}/b/x", "ba"),
            ("aaa", r"s/a\{2\}/b/x", "aaa"),
            ("a^b", "s/a^b/x/", "x"),
            ("a^b", "s/a^b/x/x", "a^b"),
            ("a$b", "s/a$b/x/", "x"),
            ("a$b", "s/a$b/x/x", "a$b"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-candidate-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression, expected_name in cases:
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

    def test_capture_backreference_and_contextual_anchors_match_gnu(self) -> None:
        success_cases = (
            ("aa", r"s/\(a\)\1/b/", "b"),
            ("aa", r"s/(a)\1/b/x", "b"),
            ("ab", r"s/\(^a\)/x/", "xb"),
            ("ab", "s/(^a)/x/x", "xb"),
            ("b", r"s/a\|^b/x/", "x"),
            ("b", "s/a|^b/x/x", "x"),
            ("a", r"s/a$\|b/x/", "x"),
            ("a", "s/a$|b/x/x", "x"),
            ("aa", "s/a*/x/", "x"),
            ("ab", "s/^a/x/", "xb"),
            ("ab", "s/b$/x/", "ax"),
            ("a+", "s/[a+]/x/", "x+"),
        )
        invalid_cases = (
            ("aa", r"s/(a)\1/b/"),
            ("aa", r"s/\(a\)\1/b/x"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-context-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression, expected_name in success_cases:
                with self.subTest(member=member_name, expression=expression):
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                        {expected_name: ("file", "")},
                    )

            for member_name, expression in invalid_cases:
                with self.subTest(invalid_expression=expression):
                    filtered = self.run_filter(candidate, member_name, expression)
                    reference = self.run_gnu(
                        work / ("invalid-" + expression.encode().hex()),
                        member_name,
                        expression,
                    )
                    self.assertNotEqual(filtered.returncode, 0)
                    self.assertEqual(filtered.stdout, b"")
                    self.assertNotEqual(reference.returncode, 0)

    def test_regex_dialects_compose_with_occurrences_and_link_scopes(self) -> None:
        cases = (
            (r"s/a\+/b/2", "aaa/b"),
            ("s/a+/b/x2", "aaa/b"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-compose-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for expression, transformed in cases:
                with self.subTest(expression=expression):
                    expected = {
                        transformed: ("file", ""),
                        "hard": ("hard", transformed),
                        "sym": ("sym", transformed),
                    }
                    self.assert_matches_gnu(
                        candidate,
                        work / expression.encode().hex(),
                        "aaa/aaa",
                        expression,
                        expected,
                        with_links=True,
                    )

    def test_unsupported_posix_bracket_forms_fail_before_archive_output(self) -> None:
        cases = (
            ("5", "s/[[:digit:]]/x/"),
            ("a", "s/[[.a.]]/x/"),
            ("a", "s/[[=a=]]/x/"),
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-regex-posix-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_candidate(
                work / "candidate-work", include_regex_patch=True
            )
            for member_name, expression in cases:
                with self.subTest(member=member_name, expression=expression):
                    filtered = self.run_filter(candidate, member_name, expression)
                    self.assertNotEqual(filtered.returncode, 0)
                    self.assertEqual(filtered.stdout, b"")
                    self.assertIn(
                        "unsupported POSIX bracket class",
                        filtered.stderr.decode("utf-8", "replace"),
                    )

                    reference = self.run_gnu(
                        work / expression.encode().hex(),
                        member_name,
                        expression,
                    )
                    self.assertEqual(
                        reference.returncode,
                        0,
                        reference.stderr.decode("utf-8", "replace"),
                    )


if __name__ == "__main__":
    unittest.main()
