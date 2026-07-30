from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


def fixture_archive() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        payload = b"strip\n"
        member = tarfile.TarInfo("./a/b/file")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


class LF14StripComponentsValidationTest(unittest.TestCase):
    def test_negative_values_are_rejected_like_gnu_tar(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )

        with tempfile.TemporaryDirectory(prefix="lf14-strip-validation-") as td:
            work = pathlib.Path(td)
            candidate = work / "candidate"
            upstream = candidate / "upstream/mmdebstrap"
            upstream.mkdir(parents=True)
            shutil.copy2(repo / "upstream/mmdebstrap/tarfilter", upstream / "tarfilter")

            for patch_name in (
                "mmdebstrap-tarfilter-preserve-gnu-sparse.patch",
                "mmdebstrap-tarfilter-transform-semantics.patch",
                "mmdebstrap-tarfilter-reject-negative-strip.patch",
            ):
                applied = subprocess.run(
                    [
                        "patch",
                        "-p1",
                        "-d",
                        str(candidate),
                        "-i",
                        str(lane / patch_name),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(
                    applied.returncode,
                    0,
                    f"{patch_name}:\n{applied.stdout}{applied.stderr}",
                )

            source = fixture_archive()
            tarfilter = upstream / "tarfilter"
            for value in (-1, -2):
                reference = subprocess.run(
                    ["tar", "-tf", "-", f"--strip-components={value}"],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(reference.returncode, 0)

                candidate_run = subprocess.run(
                    [
                        sys.executable,
                        str(tarfilter),
                        f"--strip-components={value}",
                    ],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(candidate_run.returncode, 0)
                self.assertEqual(candidate_run.stdout, b"")
                self.assertIn(b"must be non-negative", candidate_run.stderr)

            zero = subprocess.run(
                [sys.executable, str(tarfilter), "--strip-components=0"],
                input=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                zero.returncode,
                0,
                zero.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(zero.stdout, source)


if __name__ == "__main__":
    unittest.main()
