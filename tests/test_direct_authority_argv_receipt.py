from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.classify_env_argv import classify_paths, read_argv_record


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRANSACTION = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-env/direct_authority_transaction.sh"
)


def write_record(path: pathlib.Path, argv: tuple[str, ...]) -> None:
    path.write_bytes(b"\0".join(value.encode() for value in argv) + b"\0")


def summarize_dpkg_records(root: pathlib.Path) -> dict[str, object]:
    records = [
        {"path": str(path), "argv": list(read_argv_record(path))}
        for path in sorted(root.iterdir())
    ]
    vectors = [record["argv"] for record in records]
    return {
        "schema_version": 1,
        "files_checked": len(records),
        "records": records,
        "print_architecture": sum(
            argv == ["--print-architecture"] for argv in vectors
        ),
        "force_script_chrootless": sum(
            "--force-script-chrootless" in argv for argv in vectors
        ),
    }


class DirectAuthorityArgvReceiptTest(unittest.TestCase):
    def test_dpkg_receipt_matches_exact_argv_elements(self) -> None:
        with tempfile.TemporaryDirectory(prefix="direct-dpkg-argv-") as temporary:
            root = pathlib.Path(temporary)
            write_record(root / "argv.1", ("--print-architecture",))
            write_record(
                root / "argv.2",
                (
                    "--force-not-root",
                    "--force-script-chrootless",
                    "--root=/target",
                    "--install",
                    "/target/pkg.deb",
                ),
            )
            write_record(
                root / "argv.3",
                (
                    "--status-fd=7",
                    "prefix--force-script-chrootless-suffix",
                ),
            )
            summary = summarize_dpkg_records(root)

        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["files_checked"], 3)
        self.assertEqual(summary["print_architecture"], 1)
        self.assertEqual(summary["force_script_chrootless"], 1)

    def test_env_receipt_distinguishes_version_and_sanitizer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="direct-env-argv-") as temporary:
            root = pathlib.Path(temporary)
            write_record(root / "argv.1", ("--version",))
            write_record(
                root / "argv.2",
                (
                    "-i",
                    "PATH=/usr/sbin:/usr/bin:/sbin:/bin",
                    "TMPDIR=/target/tmp",
                    "dpkg",
                    "--force-script-chrootless",
                ),
            )
            write_record(
                root / "argv.3",
                (
                    "-i",
                    "PATH=/usr/bin",
                    "sh",
                    "-c",
                    "printf dpkg",
                ),
            )
            payload = classify_paths((root,))

        self.assertEqual(
            payload["counts"],
            {
                "host-version-probe": 1,
                "host-shell-hook": 0,
                "sanitizer-dpkg": 1,
                "other-host": 1,
            },
        )

    def test_empty_direct_receipt_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="direct-empty-argv-") as temporary:
            root = pathlib.Path(temporary)
            env_payload = classify_paths((root,))
            dpkg_payload = summarize_dpkg_records(root)

        self.assertEqual(env_payload["files_checked"], 0)
        self.assertEqual(sum(env_payload["counts"].values()), 0)
        self.assertEqual(dpkg_payload["files_checked"], 0)
        self.assertEqual(dpkg_payload["records"], [])

    def test_transaction_uses_lossless_env_and_dpkg_records(self) -> None:
        source = TRANSACTION.read_text(encoding="utf-8")

        # Both fake wrappers write the original argument vector, not a joined
        # display string. The exact line appears once in each heredoc.
        self.assertEqual(source.count('printf \'%s\\0\' "$@" >&9'), 2)
        self.assertNotIn('printf \'%s\\n\' "$*"', source)
        self.assertNotIn('printf \'%s\\n\' "\\$*"', source)

        self.assertIn("tools/classify_env_argv.py", source)
        self.assertIn("-dpkg-argv.json", source)
        self.assertIn("-direct-receipt.json", source)
        self.assertIn('argv == ["--print-architecture"]', source)
        self.assertIn('"--force-script-chrootless" in argv', source)
        self.assertNotIn(
            "grep -F -- '--force-script-chrootless'",
            source,
        )
        self.assertNotIn("assert_version_probe_only()", source)
        self.assertNotIn("assert_version_probe_and_sanitizer()", source)

    def test_direct_receipt_schema_is_explicit_and_lossless(self) -> None:
        source = TRANSACTION.read_text(encoding="utf-8")
        required = (
            '"schema_version": 1',
            '"files_checked": len(records)',
            '"records": records',
            '"host-version-probe"',
            '"sanitizer-dpkg"',
            '"print-architecture"',
            '"force-script-chrootless"',
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, source)

        # Ensure the JSON output itself can represent a vector containing an
        # empty argument and a newline without losing boundaries.
        payload = {
            "schema_version": 1,
            "records": [{"argv": ["", "line one\nline two"]}],
        }
        rendered = json.dumps(payload)
        self.assertEqual(json.loads(rendered), payload)


if __name__ == "__main__":
    unittest.main()
