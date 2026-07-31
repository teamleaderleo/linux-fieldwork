from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.classify_env_argv import (
    ArgvReceiptError,
    classify_argv,
    classify_paths,
    read_argv_record,
)


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRANSACTION = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-env/apt_authority_transaction.sh"
)


class EnvArgvClassifierTest(unittest.TestCase):
    @staticmethod
    def write_record(path: pathlib.Path, argv: tuple[str, ...]) -> None:
        path.write_bytes(b"\0".join(value.encode() for value in argv) + b"\0")

    def test_lossless_record_preserves_spaces_newlines_empty_and_equals(self) -> None:
        values = (
            "--unset=TMPDIR",
            "NAME=value with spaces",
            "sh",
            "-c",
            "line one\nline two",
            "exec",
            "",
        )
        with tempfile.TemporaryDirectory(prefix="env-argv-roundtrip-") as temporary:
            path = pathlib.Path(temporary) / "argv.1"
            self.write_record(path, values)
            observed = read_argv_record(path)
        self.assertEqual(observed, values)

    def test_version_probe_is_exact(self) -> None:
        self.assertEqual(
            classify_argv(("--version",)).classification,
            "host-version-probe",
        )
        self.assertEqual(
            classify_argv(("--version", "extra")).classification,
            "other-host",
        )

    def test_sanitizer_requires_ignore_environment_and_dpkg_command(self) -> None:
        record = classify_argv(
            (
                "-i",
                "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                "TMPDIR=/target/tmp",
                "dpkg",
                "--force-script-chrootless",
            )
        )
        self.assertEqual(record.classification, "sanitizer-dpkg")
        self.assertTrue(record.ignore_environment)
        self.assertEqual(record.command, "dpkg")

        for values in (
            ("PATH=/usr/bin", "dpkg", "--version"),
            ("-i", "PATH=/usr/bin", "sh", "-c", "echo dpkg"),
            ("--split-string=dpkg --version",),
        ):
            with self.subTest(values=values):
                self.assertNotEqual(
                    classify_argv(values).classification,
                    "sanitizer-dpkg",
                )

    def test_setup_hook_is_classified_by_argv_shape_not_script_text(self) -> None:
        record = classify_argv(
            (
                "--unset=TMPDIR",
                "MMDEBSTRAP_APT_CONFIG=/tmp/apt.conf",
                "sh",
                "-c",
                'mkdir -p "$1/tmp"; cp "/tmp/pkg.deb" "$1/tmp/pkg.deb"',
                "exec",
                "/target/root",
            )
        )
        self.assertEqual(record.classification, "host-shell-hook")
        self.assertEqual(record.command, "sh")

        mentions_dpkg = classify_argv(
            (
                "sh",
                "-c",
                "printf '%s\\n' dpkg",
                "exec",
                "/target/root",
            )
        )
        self.assertEqual(mentions_dpkg.classification, "host-shell-hook")
        self.assertNotEqual(mentions_dpkg.classification, "sanitizer-dpkg")

    def test_directory_summary_retains_all_classes_and_unknown_host_calls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="env-argv-summary-") as temporary:
            root = pathlib.Path(temporary)
            self.write_record(root / "argv.1", ("--version",))
            self.write_record(
                root / "argv.2",
                ("--unset=TMPDIR", "sh", "-c", "true", "exec", "/target"),
            )
            self.write_record(
                root / "argv.3",
                ("-i", "PATH=/usr/bin", "/usr/bin/dpkg", "--version"),
            )
            self.write_record(root / "argv.4", ("date", "+%s"))
            payload = classify_paths((root,))

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["files_checked"], 4)
        self.assertEqual(
            payload["counts"],
            {
                "host-version-probe": 1,
                "host-shell-hook": 1,
                "sanitizer-dpkg": 1,
                "other-host": 1,
            },
        )
        self.assertEqual(len(payload["records"]), 4)

    def test_empty_directory_is_an_explicit_zero_record_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="env-argv-empty-") as temporary:
            payload = classify_paths((pathlib.Path(temporary),))
        self.assertEqual(payload["files_checked"], 0)
        self.assertEqual(sum(payload["counts"].values()), 0)
        self.assertEqual(payload["records"], [])

    def test_missing_trailing_nul_and_symlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="env-argv-invalid-") as temporary:
            root = pathlib.Path(temporary)
            incomplete = root / "incomplete"
            incomplete.write_bytes(b"--version")
            with self.assertRaisesRegex(ArgvReceiptError, "trailing NUL"):
                read_argv_record(incomplete)

            target = root / "target"
            self.write_record(target, ("--version",))
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(ArgvReceiptError, "symbolic link"):
                read_argv_record(link)

    def test_transaction_uses_lossless_records_and_structural_json(self) -> None:
        source = TRANSACTION.read_text(encoding="utf-8")
        self.assertIn('printf \'%s\\0\' "$@" >&9', source)
        self.assertIn('tools/classify_env_argv.py', source)
        self.assertIn('outer-env.json', source)
        self.assertNotIn('printf \'%s\\n\' "$*"', source)
        self.assertNotIn("grep -F -- '-i PATH='", source)
        self.assertNotIn("assert_version_probe_only()", source)
        self.assertNotIn("assert_version_probe_and_sanitizer()", source)

        # The receipt must preserve unexpected host-side calls rather than
        # silently deleting them from the evidence.
        self.assertIn('"other-host"', source)
        self.assertIn('"host-shell-hook"', source)
        self.assertIn('"sanitizer-dpkg"', source)


if __name__ == "__main__":
    unittest.main()
