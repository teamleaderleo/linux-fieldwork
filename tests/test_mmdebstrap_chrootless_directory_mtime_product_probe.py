from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
PREPARER = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime/prepare_product_normalizer.py"
)
PROBE = (
    REPOSITORY_ROOT
    / "investigations/mmdebstrap-chrootless-directory-mtime/real_metadata_probe.sh"
)
WORKFLOW = (
    REPOSITORY_ROOT
    / ".github/workflows/mmdebstrap-chrootless-directory-mtime.yml"
)


class ChrootlessDirectoryMtimeProductProbeTest(unittest.TestCase):
    def test_preparer_applies_exact_patch_and_emits_perl_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mtime-preparer-") as temporary:
            output = pathlib.Path(temporary) / "normalizer.pl"
            completed = subprocess.run(
                ["python3", str(PREPARER), str(output)],
                cwd=REPOSITORY_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )
            source = output.read_text(encoding="utf-8")

        self.assertTrue(source.startswith("#!/usr/bin/perl\n"))
        self.assertIn("use File::Find;", source)
        self.assertIn("sub normalize_archive_directory_mtimes", source)
        self.assertIn("$File::Find::prune = 1;", source)
        self.assertIn("1 == utime($mtime, $mtime, $File::Find::name)", source)
        self.assertIn(
            "normalize_archive_directory_mtimes($ARGV[0], $ARGV[1]);",
            source,
        )
        self.assertNotIn("sub main", source)

    def test_real_probe_selects_product_helper_when_patch_exists(self) -> None:
        source = PROBE.read_text(encoding="utf-8")
        patch_check = source.index('if [[ -f "$candidate_patch" ]]; then')
        prepare = source.index("prepare_product_normalizer.py", patch_check)
        execute = source.index('perl "$product_normalizer" "$tree" "$timestamp"', prepare)
        receipt = source.index("normalizer=extracted-product-perl-helper", execute)
        fallback = source.index("normalizer=python-evidence-model")
        self.assertLess(fallback, patch_check)
        self.assertLess(patch_check, prepare)
        self.assertLess(prepare, execute)
        self.assertLess(execute, receipt)
        self.assertIn("else\n  python3 -", source)
        self.assertIn("normalizer=$normalizer", source)

    def test_candidate_workflow_requires_exact_product_receipt(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("prepare_product_normalizer.py", source)
        self.assertIn(
            "tests/test_mmdebstrap_chrootless_directory_mtime_product_probe.py",
            source,
        )
        self.assertIn(
            "normalizer=extracted-product-perl-helper",
            source,
        )
        self.assertNotIn("normalizer=python-evidence-model' \"$receipt\"", source)


if __name__ == "__main__":
    unittest.main()
