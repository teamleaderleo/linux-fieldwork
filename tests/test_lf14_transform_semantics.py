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
        member = tarfile.TarInfo("a/a")
        payload = b"transform\n"
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def transformed_names(archive: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
        return [member.name for member in handle]


class LF14TransformSemanticsTest(unittest.TestCase):
    def test_candidate_matches_gnu_tar_transform_flags(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )

        with tempfile.TemporaryDirectory(prefix="lf14-transform-") as td:
            work = pathlib.Path(td)
            candidate = work / "candidate"
            upstream = candidate / "upstream/mmdebstrap"
            upstream.mkdir(parents=True)
            shutil.copy2(repo / "upstream/mmdebstrap/tarfilter", upstream / "tarfilter")

            for patch_name in (
                "mmdebstrap-tarfilter-preserve-gnu-sparse.patch",
                "mmdebstrap-tarfilter-transform-semantics.patch",
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

            tarfilter = upstream / "tarfilter"
            source = fixture_archive()
            for expression in (
                "s/a/b/",
                "s/a/b/g",
                "s/A/b/i",
                "s/A/b/gi",
                "s/A/b/ig",
                r"s/a/b\/c/",
            ):
                reference = subprocess.run(
                    [
                        "tar",
                        "-tf",
                        "-",
                        "--show-transformed-names",
                        f"--transform={expression}",
                    ],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(
                    reference.returncode,
                    0,
                    reference.stderr.decode("utf-8", errors="replace"),
                )
                expected = reference.stdout.decode().splitlines()

                filtered = subprocess.run(
                    [sys.executable, str(tarfilter), f"--transform={expression}"],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(
                    filtered.returncode,
                    0,
                    filtered.stderr.decode("utf-8", errors="replace"),
                )
                self.assertEqual(transformed_names(filtered.stdout), expected)

            for expression in ("s/a/b/x", "s/a/b/gg", "s/a/b/ii"):
                rejected = subprocess.run(
                    [sys.executable, str(tarfilter), f"--transform={expression}"],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(rejected.returncode, 0)


if __name__ == "__main__":
    unittest.main()
