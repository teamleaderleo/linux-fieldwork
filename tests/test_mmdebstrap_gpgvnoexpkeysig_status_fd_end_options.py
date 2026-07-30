from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


STATUS = "[GNUPG:] EXPKEYSIG 0123456789ABCDEF expired key\n"
REWRITTEN = STATUS.replace("EXPKEYSIG", "GOODSIG")


class GpgvStatusFdEndOptionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="gpgv-status-fd-end-options-"
        )
        root = pathlib.Path(cls.temporary.name)
        cls.fake_bin = root / "bin"
        cls.fake_bin.mkdir()
        fake = cls.fake_bin / "gpgv"
        fake.write_text(
            """#!/bin/sh
set -eu
status_fd=1
while [ "$#" -gt 0 ]; do
  case $1 in
    --)
      break
      ;;
    --status-fd)
      status_fd=$2
      shift 2
      ;;
    --status-fd=*)
      status_fd=${1#--status-fd=}
      shift
      ;;
    *)
      shift
      ;;
  esac
done
eval 'printf %s "$FAKE_GPGV_STATUS" >&'"$status_fd"
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)

        cls.tree = root / "candidate"
        cls.wrapper = cls.tree / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.wrapper.parent.mkdir(parents=True)
        shutil.copy2(
            cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig", cls.wrapper
        )
        patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-status-fd/"
            "0001-validate-status-fd-options.patch"
        )
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=cls.tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{self.fake_bin}:/usr/bin:/bin",
                "FAKE_GPGV_STATUS": STATUS,
            }
        )
        return env

    def test_positional_status_fd_spelling_after_double_dash_is_not_parsed(self) -> None:
        result = subprocess.run(
            ["/bin/sh", str(self.wrapper), "--", "--status-fd"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment(),
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, REWRITTEN)

    def test_valid_selection_before_double_dash_survives_positional_spelling(self) -> None:
        read_fd, write_fd = os.pipe()
        try:
            result = subprocess.run(
                [
                    "/bin/sh",
                    str(self.wrapper),
                    "--status-fd",
                    str(write_fd),
                    "--",
                    "--status-fd",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment(),
                pass_fds=(write_fd,),
                timeout=10,
            )
        finally:
            os.close(write_fd)
        with os.fdopen(read_fd, encoding="utf-8") as stream:
            captured = stream.read()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(captured, REWRITTEN)

    def test_source_breaks_option_scan_at_double_dash(self) -> None:
        source = self.wrapper.read_text(encoding="utf-8")
        self.assertIn("      --)\n        break", source)


if __name__ == "__main__":
    unittest.main()
