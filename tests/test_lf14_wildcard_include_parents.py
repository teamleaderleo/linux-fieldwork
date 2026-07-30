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
    entries = (
        ("./foo", b"", tarfile.DIRTYPE),
        ("./foo/x", b"", tarfile.DIRTYPE),
        ("./foo/x/bar", b"kept\n", tarfile.REGTYPE),
        ("./other", b"", tarfile.DIRTYPE),
        ("./other/drop", b"drop\n", tarfile.REGTYPE),
    )
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, payload, member_type in entries:
            member = tarfile.TarInfo(name)
            member.type = member_type
            member.mode = 0o750 if member_type == tarfile.DIRTYPE else 0o640
            member.size = 0 if member_type == tarfile.DIRTYPE else len(payload)
            archive.addfile(
                member,
                None if member_type == tarfile.DIRTYPE else io.BytesIO(payload),
            )
    return output.getvalue()


def run_filter(tarfilter: pathlib.Path, archive: bytes) -> bytes:
    result = subprocess.run(
        [
            sys.executable,
            str(tarfilter),
            "--path-exclude=/*",
            "--path-include=/foo/*/bar",
        ],
        input=archive,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def names(archive: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
        return handle.getnames()


class LF14WildcardIncludeParentsTest(unittest.TestCase):
    def test_wildcard_include_retains_intermediate_parents(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )

        with tempfile.TemporaryDirectory(prefix="lf14-wildcard-parent-") as td:
            work = pathlib.Path(td)
            candidate = work / "candidate"
            upstream = candidate / "upstream/mmdebstrap"
            upstream.mkdir(parents=True)
            shutil.copy2(repo / "upstream/mmdebstrap/tarfilter", upstream / "tarfilter")

            base_patch = lane / "mmdebstrap-tarfilter-preserve-gnu-sparse.patch"
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate), "-i", str(base_patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            source = fixture_archive()
            incomplete = names(run_filter(upstream / "tarfilter", source))
            self.assertIn("./foo", incomplete)
            self.assertNotIn("./foo/x", incomplete)
            self.assertIn("./foo/x/bar", incomplete)

            followup = lane / "mmdebstrap-tarfilter-wildcard-parent.patch"
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate), "-i", str(followup)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            repaired = names(run_filter(upstream / "tarfilter", source))
            self.assertEqual(repaired, ["./foo", "./foo/x", "./foo/x/bar"])

            with tarfile.open(
                fileobj=io.BytesIO(run_filter(upstream / "tarfilter", source)),
                mode="r:*",
            ) as archive:
                self.assertEqual(archive.getmember("./foo").mode, 0o750)
                self.assertEqual(archive.getmember("./foo/x").mode, 0o750)


if __name__ == "__main__":
    unittest.main()
