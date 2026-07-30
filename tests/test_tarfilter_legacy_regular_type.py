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
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        entries = (
            ("zero-regular", tarfile.REGTYPE, b"zero\n"),
            ("nul-regular", tarfile.AREGTYPE, b"nul\n"),
        )
        for name, member_type, payload in entries:
            member = tarfile.TarInfo(name)
            member.type = member_type
            member.size = len(payload)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(payload))

        directory = tarfile.TarInfo("directory")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        archive.addfile(directory)
    return output.getvalue()


def inspect_archive(data: bytes) -> dict[str, bytes]:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        return {member.name: member.type for member in archive}


def run_filter(tarfilter: pathlib.Path, source: bytes, type_name: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(tarfilter), f"--type-exclude={type_name}"],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TarfilterLegacyRegularTypeTest(unittest.TestCase):
    def test_regtype_excludes_zero_and_nul_regular_members(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source = repo / "upstream/mmdebstrap/tarfilter"
        patch_file = repo / (
            "investigations/tarfilter-legacy-regular-type-filter/"
            "tarfilter-legacy-regular-type-filter.patch"
        )
        fixture = fixture_archive()

        parsed_fixture = inspect_archive(fixture)
        self.assertEqual(parsed_fixture["zero-regular"], tarfile.REGTYPE)
        self.assertEqual(parsed_fixture["nul-regular"], tarfile.AREGTYPE)
        self.assertEqual(parsed_fixture["directory"], tarfile.DIRTYPE)

        baseline = run_filter(source, fixture, "REGTYPE")
        self.assertEqual(
            baseline.returncode,
            0,
            baseline.stderr.decode("utf-8", errors="replace"),
        )
        baseline_members = inspect_archive(baseline.stdout)
        self.assertNotIn("zero-regular", baseline_members)
        self.assertIn(
            "nul-regular",
            baseline_members,
            "negative control: unmodified source must leak AREGTYPE",
        )
        self.assertIn("directory", baseline_members)

        with tempfile.TemporaryDirectory(prefix="tarfilter-aregtype-") as td:
            work = pathlib.Path(td)
            candidate_repo = work / "candidate"
            candidate = candidate_repo / "upstream/mmdebstrap/tarfilter"
            candidate.parent.mkdir(parents=True)
            shutil.copy2(source, candidate)

            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            for spelling in ("REGTYPE", "0"):
                filtered = run_filter(candidate, fixture, spelling)
                self.assertEqual(
                    filtered.returncode,
                    0,
                    filtered.stderr.decode("utf-8", errors="replace"),
                )
                self.assertEqual(
                    inspect_archive(filtered.stdout),
                    {"directory": tarfile.DIRTYPE},
                )

            directory_filtered = run_filter(candidate, fixture, "DIRTYPE")
            self.assertEqual(
                directory_filtered.returncode,
                0,
                directory_filtered.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(
                inspect_archive(directory_filtered.stdout),
                {
                    "zero-regular": tarfile.REGTYPE,
                    "nul-regular": tarfile.AREGTYPE,
                },
            )


if __name__ == "__main__":
    unittest.main()
