from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


LARGE_UID = 1_000_000_000
LARGE_GID = 1_000_000_001
SMALL_UID = 1000
SMALL_GID = 1001
SHIFT = 7


def fixture_archive() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, uid, gid, payload in (
            ("large", LARGE_UID, LARGE_GID, b"large\n"),
            ("small", SMALL_UID, SMALL_GID, b"small\n"),
        ):
            member = tarfile.TarInfo(name)
            member.uid = uid
            member.gid = gid
            member.size = len(payload)
            member.mode = 0o640
            archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def inspect_archive(data: bytes) -> dict[str, tuple[int, int, dict[str, str], bytes]]:
    result: dict[str, tuple[int, int, dict[str, str], bytes]] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
        for member in archive:
            extracted = archive.extractfile(member)
            payload = b"" if extracted is None else extracted.read()
            result[member.name] = (
                member.uid,
                member.gid,
                dict(member.pax_headers),
                payload,
            )
    return result


def run_filter(
    tarfilter: pathlib.Path, source: bytes, shift: int
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(tarfilter), f"--idshift={shift}"],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class TarfilterPaxIdshiftTest(unittest.TestCase):
    def test_candidate_regenerates_shifted_pax_ids(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source = repo / "upstream/mmdebstrap/tarfilter"
        patch_file = repo / (
            "investigations/tarfilter-pax-idshift/"
            "tarfilter-pax-idshift.patch"
        )
        fixture = fixture_archive()
        original = inspect_archive(fixture)

        self.assertEqual(original["large"][0:2], (LARGE_UID, LARGE_GID))
        self.assertEqual(original["large"][2].get("uid"), str(LARGE_UID))
        self.assertEqual(original["large"][2].get("gid"), str(LARGE_GID))
        self.assertNotIn("uid", original["small"][2])
        self.assertNotIn("gid", original["small"][2])

        baseline = run_filter(source, fixture, SHIFT)
        self.assertEqual(
            baseline.returncode,
            0,
            baseline.stderr.decode("utf-8", errors="replace"),
        )
        baseline_members = inspect_archive(baseline.stdout)
        self.assertEqual(
            baseline_members["large"][0:2],
            (LARGE_UID, LARGE_GID),
            "negative control: stale PAX values must override the shifted fields",
        )
        self.assertEqual(
            baseline_members["small"][0:2],
            (SMALL_UID + SHIFT, SMALL_GID + SHIFT),
        )

        with tempfile.TemporaryDirectory(prefix="tarfilter-pax-idshift-") as td:
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

            shifted = run_filter(candidate, fixture, SHIFT)
            self.assertEqual(
                shifted.returncode,
                0,
                shifted.stderr.decode("utf-8", errors="replace"),
            )
            shifted_members = inspect_archive(shifted.stdout)
            self.assertEqual(
                shifted_members["large"][0:2],
                (LARGE_UID + SHIFT, LARGE_GID + SHIFT),
            )
            self.assertEqual(
                shifted_members["large"][2].get("uid"),
                str(LARGE_UID + SHIFT),
            )
            self.assertEqual(
                shifted_members["large"][2].get("gid"),
                str(LARGE_GID + SHIFT),
            )
            self.assertEqual(
                shifted_members["small"][0:2],
                (SMALL_UID + SHIFT, SMALL_GID + SHIFT),
            )
            self.assertEqual(shifted_members["large"][3], original["large"][3])
            self.assertEqual(shifted_members["small"][3], original["small"][3])

            roundtrip = run_filter(candidate, shifted.stdout, -SHIFT)
            self.assertEqual(
                roundtrip.returncode,
                0,
                roundtrip.stderr.decode("utf-8", errors="replace"),
            )
            roundtrip_members = inspect_archive(roundtrip.stdout)
            for name in ("large", "small"):
                self.assertEqual(roundtrip_members[name][0:2], original[name][0:2])
                self.assertEqual(roundtrip_members[name][3], original[name][3])


if __name__ == "__main__":
    unittest.main()
