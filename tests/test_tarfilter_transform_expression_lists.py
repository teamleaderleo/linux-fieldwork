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


class TarfilterTransformExpressionListTest(unittest.TestCase):
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
    def input_archive() -> bytes:
        output = io.BytesIO()
        payload = b"payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            target = tarfile.TarInfo("prefix/target")
            target.size = len(payload)
            archive.addfile(target, io.BytesIO(payload))

            hard = tarfile.TarInfo("prefix/hard")
            hard.type = tarfile.LNKTYPE
            hard.linkname = "prefix/target"
            archive.addfile(hard)

            sym = tarfile.TarInfo("sym")
            sym.type = tarfile.SYMTYPE
            sym.linkname = "prefix/target"
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

    def run_predecessor(
        self,
        candidate: pathlib.Path,
        expressions: list[str],
    ) -> tuple[int, Snapshot | None, str]:
        command = [sys.executable, str(candidate)]
        for expression in expressions:
            command.extend(("--transform", expression))
        completed = subprocess.run(
            command,
            input=self.input_archive(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = self.snapshot(completed.stdout) if completed.returncode == 0 else None
        return (
            completed.returncode,
            result,
            completed.stderr.decode("utf-8", "replace"),
        )

    @staticmethod
    def run_gnu(
        work: pathlib.Path,
        expressions: list[str],
    ) -> tuple[int, Snapshot | None, str]:
        root = work / "root"
        archive_path = work / "gnu.tar"
        target = root / "prefix/target"
        target.parent.mkdir(parents=True)
        target.write_text("payload\n")
        os.link(target, root / "prefix/hard")
        os.symlink("prefix/target", root / "sym")

        command = ["tar", "--format=pax"]
        for expression in expressions:
            command.extend(("--transform", expression))
        command.extend(
            (
                "-cf",
                str(archive_path),
                "-C",
                str(root),
                "prefix/target",
                "prefix/hard",
                "sym",
            )
        )
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env={"LC_ALL": "C", "PATH": "/usr/bin"},
        )
        result = None
        if completed.returncode == 0:
            with archive_path.open("rb") as stream:
                result = TarfilterTransformExpressionListTest.snapshot(stream.read())
        return completed.returncode, result, completed.stderr

    def test_repeated_options_work_but_one_expression_list_is_rejected(self) -> None:
        combined = ["s,^prefix/,,;s,^target$,final,"]
        repeated = ["s,^prefix/,,", "s,^target$,final,"]
        expected: Snapshot = {
            "final": ("file", ""),
            "hard": ("hard", "final"),
            "sym": ("sym", "final"),
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-expression-list-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")

            pred_combined_rc, pred_combined, _ = self.run_predecessor(
                candidate, combined
            )
            self.assertNotEqual(pred_combined_rc, 0)
            self.assertIsNone(pred_combined)

            pred_repeated_rc, pred_repeated, pred_repeated_err = self.run_predecessor(
                candidate, repeated
            )
            self.assertEqual(pred_repeated_rc, 0, pred_repeated_err)
            self.assertEqual(pred_repeated, expected)

            gnu_combined_rc, gnu_combined, gnu_combined_err = self.run_gnu(
                work / "gnu-combined", combined
            )
            self.assertEqual(gnu_combined_rc, 0, gnu_combined_err)
            self.assertEqual(gnu_combined, expected)

            gnu_repeated_rc, gnu_repeated, gnu_repeated_err = self.run_gnu(
                work / "gnu-repeated", repeated
            )
            self.assertEqual(gnu_repeated_rc, 0, gnu_repeated_err)
            self.assertEqual(gnu_repeated, expected)

    def test_predecessor_rejects_persistent_scope_statements(self) -> None:
        cases: dict[str, Snapshot] = {
            "flags=r;s,^prefix/,,": {
                "target": ("file", ""),
                "hard": ("hard", "prefix/target"),
                "sym": ("sym", "prefix/target"),
            },
            "flags=s;s,^prefix/,,": {
                "prefix/target": ("file", ""),
                "prefix/hard": ("hard", "prefix/target"),
                "sym": ("sym", "target"),
            },
            "flags=h;s,^prefix/,,": {
                "prefix/target": ("file", ""),
                "prefix/hard": ("hard", "target"),
                "sym": ("sym", "prefix/target"),
            },
            "flags=rh;s,^prefix/,,": {
                "target": ("file", ""),
                "hard": ("hard", "target"),
                "sym": ("sym", "prefix/target"),
            },
            "flags=rs;s,^prefix/,,": {
                "target": ("file", ""),
                "hard": ("hard", "prefix/target"),
                "sym": ("sym", "target"),
            },
            "flags=sh;s,^prefix/,,": {
                "prefix/target": ("file", ""),
                "prefix/hard": ("hard", "target"),
                "sym": ("sym", "target"),
            },
            "flags=rsh;s,^prefix/,,": {
                "target": ("file", ""),
                "hard": ("hard", "target"),
                "sym": ("sym", "target"),
            },
            "flags=;s,^prefix/,,": {
                "prefix/target": ("file", ""),
                "prefix/hard": ("hard", "prefix/target"),
                "sym": ("sym", "prefix/target"),
            },
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-persistent-scopes-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for expression, expected in cases.items():
                with self.subTest(expression=expression):
                    pred_rc, pred_result, _ = self.run_predecessor(
                        candidate, [expression]
                    )
                    self.assertNotEqual(pred_rc, 0)
                    self.assertIsNone(pred_result)

                    gnu_rc, gnu_result, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), [expression]
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(gnu_result, expected)

    def test_persistent_resets_and_local_scope_amendments(self) -> None:
        cases: dict[str, Snapshot] = {
            "flags=S;s,^prefix/,,;flags=s;s,^prefix/,,": {
                "prefix/target": ("file", ""),
                "prefix/hard": ("hard", "prefix/target"),
                "sym": ("sym", "target"),
            },
            "flags=r;s,^prefix/,,;flags=h;s,^prefix/,,": {
                "target": ("file", ""),
                "hard": ("hard", "target"),
                "sym": ("sym", "prefix/target"),
            },
            "flags=r;s,^prefix/,,H": {
                "target": ("file", ""),
                "hard": ("hard", "prefix/target"),
                "sym": ("sym", "prefix/target"),
            },
            "flags=s;s,^prefix/,,r": {
                "target": ("file", ""),
                "hard": ("hard", "prefix/target"),
                "sym": ("sym", "target"),
            },
            "flags=rsh;s,^prefix/,,;flags=s;s,^target$,final,": {
                "target": ("file", ""),
                "hard": ("hard", "target"),
                "sym": ("sym", "final"),
            },
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-scope-state-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for expression, expected in cases.items():
                with self.subTest(expression=expression):
                    pred_rc, pred_result, _ = self.run_predecessor(
                        candidate, [expression]
                    )
                    self.assertNotEqual(pred_rc, 0)
                    self.assertIsNone(pred_result)

                    gnu_rc, gnu_result, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), [expression]
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(gnu_result, expected)

    def test_statement_boundaries_require_delimiter_state(self) -> None:
        default_expected: Snapshot = {
            "target": ("file", ""),
            "hard": ("hard", "target"),
            "sym": ("sym", "target"),
        }
        field_semicolon_expected: Snapshot = {
            "pre;fix/target": ("file", ""),
            "pre;fix/hard": ("hard", "pre;fix/target"),
            "sym": ("sym", "pre;fix/target"),
        }
        with tempfile.TemporaryDirectory(prefix="tarfilter-statement-boundary-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")

            for expression in ("s;^prefix/;;", "s,^prefix/,pre;fix/,"):
                with self.subTest(shared_expression=expression):
                    pred_rc, pred_result, pred_err = self.run_predecessor(
                        candidate, [expression]
                    )
                    self.assertEqual(pred_rc, 0, pred_err)
                    expected = (
                        default_expected
                        if expression == "s;^prefix/;;"
                        else field_semicolon_expected
                    )
                    self.assertEqual(pred_result, expected)

                    gnu_rc, gnu_result, gnu_err = self.run_gnu(
                        work / expression.encode().hex(), [expression]
                    )
                    self.assertEqual(gnu_rc, 0, gnu_err)
                    self.assertEqual(gnu_result, expected)

            trailing = "s,^prefix/,,;"
            pred_rc, pred_result, _ = self.run_predecessor(candidate, [trailing])
            self.assertNotEqual(pred_rc, 0)
            self.assertIsNone(pred_result)
            gnu_rc, gnu_result, gnu_err = self.run_gnu(
                work / "trailing", [trailing]
            )
            self.assertEqual(gnu_rc, 0, gnu_err)
            self.assertEqual(gnu_result, default_expected)

            for expression in (";s,^prefix/,,", "s,^prefix/,,;;s,^target$,final,"):
                with self.subTest(rejected_expression=expression):
                    gnu_rc, gnu_result, _ = self.run_gnu(
                        work / expression.encode().hex(), [expression]
                    )
                    self.assertNotEqual(gnu_rc, 0)
                    self.assertIsNone(gnu_result)

    def test_flags_statement_rejects_non_scope_letters(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tarfilter-flags-rejection-") as td:
            work = pathlib.Path(td)
            candidate = self.prepare_predecessor(work / "predecessor")
            for expression in ("flags=x;s,^prefix/,,", "flags=g;s,^prefix/,,"):
                with self.subTest(expression=expression):
                    pred_rc, pred_result, _ = self.run_predecessor(
                        candidate, [expression]
                    )
                    self.assertNotEqual(pred_rc, 0)
                    self.assertIsNone(pred_result)

                    gnu_rc, gnu_result, _ = self.run_gnu(
                        work / expression.encode().hex(), [expression]
                    )
                    self.assertNotEqual(gnu_rc, 0)
                    self.assertIsNone(gnu_result)


if __name__ == "__main__":
    unittest.main()
