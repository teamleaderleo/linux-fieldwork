import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "mmdebstrap" / "debian" / "tests" / "testsuite"
PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-exact-subid-user-match"
    / "0001-match-subid-user-field-exactly.patch"
)


def extract_block(text: str, path: str) -> str:
    pattern = re.compile(
        rf"if \[ ! -e {re.escape(path)} \].*?\n"
        rf"\techo .*? >> {re.escape(path)}\n"
        r"fi",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"no subordinate-ID block for {path}")
    return match.group(0)


class MmdebstrapSubidAccountMatchTests(unittest.TestCase):
    def apply_candidate(self) -> str:
        tempdir = tempfile.TemporaryDirectory(prefix="mmdebstrap-subid-match-")
        self.addCleanup(tempdir.cleanup)
        tree = pathlib.Path(tempdir.name) / "tree"
        destination = tree / "upstream/mmdebstrap/debian/tests"
        destination.mkdir(parents=True)
        candidate = destination / "testsuite"
        shutil.copy2(SOURCE, candidate)
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
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        syntax = subprocess.run(
            ["/bin/sh", "-n", str(candidate)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
        return candidate.read_text(encoding="utf-8")

    def run_block(
        self,
        block: str,
        source_path: str,
        actual_path: pathlib.Path,
        user: str,
    ) -> subprocess.CompletedProcess[str]:
        script = block.replace(source_path, shlex.quote(str(actual_path)))
        env = os.environ.copy()
        env["AUTOPKGTEST_NORMAL_USER"] = user
        return subprocess.run(
            ["/bin/sh", "-eu", "-c", script],
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

    def exercise_cases(self, source_path: str) -> None:
        candidate = self.apply_candidate()
        block = extract_block(candidate, source_path)

        with tempfile.TemporaryDirectory(prefix="mmdebstrap-subid-cases-") as tmp:
            tmp_path = pathlib.Path(tmp)

            exact = tmp_path / "exact"
            exact.write_text("debci:200000:65536\n", encoding="utf-8")
            result = self.run_block(block, source_path, exact, "debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(exact.read_text(encoding="utf-8"), "debci:200000:65536\n")

            substring = tmp_path / "substring"
            substring.write_text("old-debci-helper:200000:65536\n", encoding="utf-8")
            result = self.run_block(block, source_path, substring, "debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                substring.read_text(encoding="utf-8"),
                "old-debci-helper:200000:65536\ndebci:100000:65536\n",
            )

            malformed = tmp_path / "malformed"
            malformed.write_text("debci\n", encoding="utf-8")
            result = self.run_block(block, source_path, malformed, "debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                malformed.read_text(encoding="utf-8"),
                "debci\ndebci:100000:65536\n",
            )

            literal = tmp_path / "literal"
            literal.write_text("debci123:200000:65536\n", encoding="utf-8")
            result = self.run_block(block, source_path, literal, "debci.*")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                literal.read_text(encoding="utf-8").endswith(
                    "debci.*:100000:65536\n"
                )
            )

            leading_option = tmp_path / "leading-option"
            leading_option.write_text("-debci:200000:65536\n", encoding="utf-8")
            result = self.run_block(block, source_path, leading_option, "-debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                leading_option.read_text(encoding="utf-8"),
                "-debci:200000:65536\n",
            )

            empty = tmp_path / "empty"
            empty.write_text("", encoding="utf-8")
            result = self.run_block(block, source_path, empty, "debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(empty.read_text(encoding="utf-8"), "debci:100000:65536\n")

            absent = tmp_path / "absent"
            result = self.run_block(block, source_path, absent, "debci")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(absent.read_text(encoding="utf-8"), "debci:100000:65536\n")

            rerun = self.run_block(block, source_path, absent, "debci")
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertEqual(absent.read_text(encoding="utf-8"), "debci:100000:65536\n")

    def test_baseline_uses_unanchored_regular_expression_grep(self) -> None:
        baseline = SOURCE.read_text(encoding="utf-8")
        self.assertIn('grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid', baseline)
        self.assertIn('grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid', baseline)

    def test_candidate_changes_only_the_two_match_conditions(self) -> None:
        baseline = SOURCE.read_text(encoding="utf-8").splitlines()
        candidate = self.apply_candidate().splitlines()
        self.assertEqual(
            len(candidate),
            len(baseline),
            "candidate unexpectedly inserted or removed testsuite lines",
        )
        differences = [
            (index + 1, before, after)
            for index, (before, after) in enumerate(zip(baseline, candidate, strict=True))
            if before != after
        ]
        self.assertEqual(len(differences), 2)
        for _line, before, after in differences:
            self.assertIn('grep "$AUTOPKGTEST_NORMAL_USER"', before)
            self.assertIn("cut -s -d: -f1", after)
            self.assertIn('grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"', after)

    def test_subuid_exact_match_and_idempotency(self) -> None:
        self.exercise_cases("/etc/subuid")

    def test_subgid_exact_match_and_idempotency(self) -> None:
        self.exercise_cases("/etc/subgid")


if __name__ == "__main__":
    unittest.main()
