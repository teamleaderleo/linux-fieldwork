from __future__ import annotations

import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_tarfilter(tarfilter: pathlib.Path, archive: bytes, *args: str) -> bytes:
    result = subprocess.run(
        [sys.executable, str(tarfilter), *args],
        input=archive,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def path_fixture() -> bytes:
    output = io.BytesIO()
    entries = (
        ("./foo", b"", tarfile.DIRTYPE),
        ("./foo/bar", b"bar", tarfile.REGTYPE),
        ("./.secret", b"dot", tarfile.REGTYPE),
        ("./secret", b"plain", tarfile.REGTYPE),
        ("../etc/passwd", b"not-host", tarfile.REGTYPE),
    )
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, content, member_type in entries:
            member = tarfile.TarInfo(name)
            member.type = member_type
            member.mode = 0o755 if member_type == tarfile.DIRTYPE else 0o644
            member.size = 0 if member_type == tarfile.DIRTYPE else len(content)
            archive.addfile(
                member,
                None if member_type == tarfile.DIRTYPE else io.BytesIO(content),
            )
    return output.getvalue()


def member_names(archive: bytes) -> set[str]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
        return {member.name for member in handle}


class LF14SparseRepairTest(unittest.TestCase):
    def test_candidate_preserves_gnu_sparse_member(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane_relative = pathlib.Path(
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )
        lane = repo / lane_relative

        with tempfile.TemporaryDirectory(prefix="lf14-sparse-repair-") as td:
            work = pathlib.Path(td)
            candidate_repo = work / "candidate"
            upstream = candidate_repo / "upstream/mmdebstrap"
            candidate_lane = candidate_repo / lane_relative
            upstream.mkdir(parents=True)
            shutil.copy2(repo / "upstream/mmdebstrap/tarfilter", upstream / "tarfilter")
            shutil.copytree(lane, candidate_lane)

            patch = candidate_lane / "mmdebstrap-tarfilter-preserve-gnu-sparse.patch"
            runner = candidate_lane / "run-probes.py"
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            output = work / "run"
            probe = subprocess.run(
                [
                    sys.executable,
                    str(runner),
                    "--repo-root",
                    str(candidate_repo),
                    "--output",
                    str(output),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(probe.returncode, 0, probe.stdout + probe.stderr)

            results = json.loads((output / "extraction-results.json").read_text())
            failures = [row for row in results if not row["pass"]]
            self.assertEqual(failures, [])

            direct = next(
                row
                for row in results
                if row["path"] == "gnu-tar-direct" and row["case"] == "sparse"
            )
            filtered = next(
                row
                for row in results
                if row["path"] == "mmdebstrap-tarfilter"
                and row["case"] == "sparse"
            )
            direct_file = direct["details"]["file"]
            filtered_file = filtered["details"]["file"]
            self.assertEqual(filtered_file["size"], direct_file["size"])
            self.assertLess(filtered_file["allocated_bytes"], filtered_file["size"] // 4)
            self.assertLessEqual(
                filtered_file["allocated_bytes"], direct_file["allocated_bytes"] * 4
            )

            direct_path = (
                output
                / "extracts/gnu-tar-direct/sparse/target/.sparse-source"
            )
            filtered_path = (
                output
                / "extracts/mmdebstrap-tarfilter/sparse/target/.sparse-source"
            )
            self.assertEqual(sha256(filtered_path), sha256(direct_path))
            for path in (direct_path, filtered_path):
                with path.open("rb") as stream:
                    for offset, expected in (
                        (0, b"BEGIN"),
                        (1024 * 1024, b"MIDDLE"),
                        (8 * 1024 * 1024, b"END"),
                    ):
                        stream.seek(offset)
                        self.assertEqual(stream.read(len(expected)), expected)
                    for offset in (4096, 2 * 1024 * 1024):
                        stream.seek(offset)
                        self.assertEqual(stream.read(32), b"\0" * 32)

            original_archive = output / "fixtures/sparse.tar"
            filtered_archive = output / "filtered/sparse.tar"
            self.assertLess(filtered_archive.stat().st_size, filtered_file["size"] // 4)
            self.assertLessEqual(
                filtered_archive.stat().st_size, original_archive.stat().st_size * 2
            )

            dense_archive = work / "dense-sparse-member.tar"
            with original_archive.open("rb") as source, dense_archive.open("wb") as target:
                dense = subprocess.run(
                    [
                        sys.executable,
                        str(upstream / "tarfilter"),
                        "--pax-exclude=GNU.sparse.name",
                    ],
                    stdin=source,
                    stdout=target,
                    stderr=subprocess.PIPE,
                )
            self.assertEqual(
                dense.returncode,
                0,
                dense.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(dense_archive, "r:*") as archive:
                member = archive.getmember(".sparse-source")
                self.assertIsNone(member.sparse)
                self.assertFalse(
                    any(key.startswith("GNU.sparse.") for key in member.pax_headers)
                )

            dense_target = work / "dense-target"
            dense_target.mkdir()
            extracted = subprocess.run(
                ["tar", "-xf", str(dense_archive), "-C", str(dense_target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            dense_path = dense_target / ".sparse-source"
            self.assertEqual(sha256(dense_path), sha256(direct_path))
            self.assertGreater(dense_archive.stat().st_size, direct_file["size"])

            tarfilter = upstream / "tarfilter"
            fixture = path_fixture()
            self.assertEqual(run_tarfilter(tarfilter, fixture), fixture)
            self.assertEqual(run_tarfilter(tarfilter, fixture, "--idshift", "0"), fixture)

            names = member_names(
                run_tarfilter(tarfilter, fixture, "--path-exclude=/.secret")
            )
            self.assertNotIn("./.secret", names)
            self.assertIn("./secret", names)

            names = member_names(
                run_tarfilter(tarfilter, fixture, "--path-exclude=/secret")
            )
            self.assertNotIn("./secret", names)
            self.assertIn("./.secret", names)

            names = member_names(
                run_tarfilter(
                    tarfilter,
                    fixture,
                    "--path-exclude=/*",
                    "--path-include=/foo/bar",
                )
            )
            self.assertIn("./foo", names)
            self.assertIn("./foo/bar", names)

            names = member_names(
                run_tarfilter(tarfilter, fixture, "--path-exclude=/etc/passwd")
            )
            self.assertIn("../etc/passwd", names)


if __name__ == "__main__":
    unittest.main()
