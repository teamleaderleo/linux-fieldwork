from __future__ import annotations

import hashlib
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


def write_sparse_file(path: pathlib.Path) -> None:
    with path.open("wb") as stream:
        stream.write(b"BEGIN")
        stream.seek(1024 * 1024)
        stream.write(b"MIDDLE")
        stream.seek(8 * 1024 * 1024)
        stream.write(b"END")


def run_tarfilter(
    tarfilter: pathlib.Path,
    source: pathlib.Path,
    target: pathlib.Path,
    *options: str,
) -> subprocess.CompletedProcess[bytes]:
    with source.open("rb") as input_stream, target.open("wb") as output_stream:
        return subprocess.run(
            [sys.executable, str(tarfilter), *options],
            stdin=input_stream,
            stdout=output_stream,
            stderr=subprocess.PIPE,
        )


def extract_archive(
    archive: pathlib.Path, target: pathlib.Path
) -> subprocess.CompletedProcess[str]:
    target.mkdir()
    return subprocess.run(
        ["tar", "-xf", str(archive), "-C", str(target)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


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

            old_source = work / "old-gnu-source"
            write_sparse_file(old_source)
            old_archive = work / "old-gnu-sparse.tar"
            subprocess.run(
                [
                    "tar",
                    "--format=gnu",
                    "--sparse",
                    "--numeric-owner",
                    "--owner=0",
                    "--group=0",
                    "-cf",
                    str(old_archive),
                    "-C",
                    str(work),
                    old_source.name,
                ],
                check=True,
            )
            with tarfile.open(old_archive, "r:*") as archive:
                old_member = archive.getmember(old_source.name)
                self.assertEqual(old_member.type, tarfile.GNUTYPE_SPARSE)
                self.assertIsNotNone(old_member.sparse)

            baseline_archive = work / "old-gnu-baseline-filtered.tar"
            baseline = run_tarfilter(
                upstream / "tarfilter",
                old_archive,
                baseline_archive,
                "--path-exclude=/__lf14_never_match__",
            )
            baseline_normalized = False
            if baseline.returncode == 0:
                try:
                    with tarfile.open(baseline_archive, "r:*") as archive:
                        member = archive.getmember(old_source.name)
                        baseline_normalized = (
                            member.type == tarfile.REGTYPE
                            and member.sparse is not None
                        )
                except tarfile.TarError:
                    pass
            self.assertFalse(
                baseline_normalized,
                "unmodified tarfilter unexpectedly met the repaired invariant",
            )

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
            self.assertLess(
                filtered_file["allocated_bytes"], filtered_file["size"] // 4
            )
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
            self.assertLess(
                filtered_archive.stat().st_size, filtered_file["size"] // 4
            )
            self.assertLessEqual(
                filtered_archive.stat().st_size, original_archive.stat().st_size * 2
            )

            dense_archive = work / "dense-sparse-member.tar"
            dense = run_tarfilter(
                upstream / "tarfilter",
                original_archive,
                dense_archive,
                "--pax-exclude=GNU.sparse.name",
            )
            self.assertEqual(
                dense.returncode,
                0,
                dense.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(dense_archive, "r:*") as archive:
                member = archive.getmember(".sparse-source")
                self.assertEqual(member.type, tarfile.REGTYPE)
                self.assertIsNone(member.sparse)
                self.assertFalse(
                    any(key.startswith("GNU.sparse.") for key in member.pax_headers)
                )

            dense_target = work / "dense-target"
            extracted = extract_archive(dense_archive, dense_target)
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            dense_path = dense_target / ".sparse-source"
            self.assertEqual(sha256(dense_path), sha256(direct_path))
            self.assertGreater(dense_archive.stat().st_size, direct_file["size"])

            old_filtered_archive = work / "old-gnu-filtered.tar"
            old_filtered = run_tarfilter(
                upstream / "tarfilter",
                old_archive,
                old_filtered_archive,
                "--path-exclude=/__lf14_never_match__",
            )
            self.assertEqual(
                old_filtered.returncode,
                0,
                old_filtered.stderr.decode("utf-8", "replace"),
            )
            listed = subprocess.run(
                ["tar", "-tf", str(old_filtered_archive)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(listed.returncode, 0, listed.stdout + listed.stderr)
            with tarfile.open(old_filtered_archive, "r:*") as archive:
                member = archive.getmember(old_source.name)
                self.assertEqual(member.type, tarfile.REGTYPE)
                self.assertIsNotNone(member.sparse)

            old_sparse_target = work / "old-gnu-sparse-target"
            extracted = extract_archive(old_filtered_archive, old_sparse_target)
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            old_sparse_path = old_sparse_target / old_source.name
            self.assertEqual(sha256(old_sparse_path), sha256(old_source))
            self.assertLess(
                old_sparse_path.stat().st_blocks * 512,
                old_sparse_path.stat().st_size // 4,
            )
            self.assertLess(
                old_filtered_archive.stat().st_size,
                old_sparse_path.stat().st_size // 4,
            )

            old_dense_archive = work / "old-gnu-dense.tar"
            old_dense = run_tarfilter(
                upstream / "tarfilter",
                old_archive,
                old_dense_archive,
                "--pax-exclude=GNU.sparse.name",
            )
            self.assertEqual(
                old_dense.returncode,
                0,
                old_dense.stderr.decode("utf-8", "replace"),
            )
            with tarfile.open(old_dense_archive, "r:*") as archive:
                member = archive.getmember(old_source.name)
                self.assertEqual(member.type, tarfile.REGTYPE)
                self.assertIsNone(member.sparse)
                self.assertFalse(
                    any(key.startswith("GNU.sparse.") for key in member.pax_headers)
                )

            old_dense_target = work / "old-gnu-dense-target"
            extracted = extract_archive(old_dense_archive, old_dense_target)
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            old_dense_path = old_dense_target / old_source.name
            self.assertEqual(sha256(old_dense_path), sha256(old_source))
            self.assertGreater(old_dense_archive.stat().st_size, old_source.stat().st_size)


if __name__ == "__main__":
    unittest.main()
