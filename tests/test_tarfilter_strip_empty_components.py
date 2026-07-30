from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


def fixture_archive(name: str) -> bytes:
    output = io.BytesIO()
    payload = b"payload\n"
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        member.mode = 0o644
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def run_filter(
    tarfilter: pathlib.Path, source: bytes, count: int
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(tarfilter), f"--strip-components={count}"],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def member_names(source: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:*") as archive:
        return archive.getnames()


def gnu_transformed_name(source: bytes, count: int, root: pathlib.Path) -> str:
    archive_path = root / "reference.tar"
    archive_path.write_bytes(source)
    result = subprocess.run(
        [
            "tar",
            "-tf",
            str(archive_path),
            f"--strip-components={count}",
            "--show-transformed-names",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    lines = result.stdout.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise AssertionError(
            f"expected one nonempty GNU transformed name, got {lines!r}: {result.stderr}"
        )
    return lines[0]


def gnu_extracts_nothing(source: bytes, count: int, root: pathlib.Path) -> bool:
    archive_path = root / "omitted-reference.tar"
    archive_path.write_bytes(source)
    target = root / "reference-target"
    target.mkdir()
    result = subprocess.run(
        [
            "tar",
            "-xf",
            str(archive_path),
            "-C",
            str(target),
            f"--strip-components={count}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return not any(target.rglob("*"))


class TarfilterStripEmptyComponentsTest(unittest.TestCase):
    def test_candidate_counts_nonempty_components_like_gnu_tar(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source = repo / "upstream/mmdebstrap/tarfilter"
        patch_file = repo / (
            "investigations/tarfilter-strip-empty-components/"
            "tarfilter-strip-empty-components.patch"
        )

        repeated = fixture_archive("a//b/file")
        baseline = run_filter(source, repeated, 2)
        self.assertEqual(
            baseline.returncode,
            0,
            baseline.stderr.decode("utf-8", errors="replace"),
        )
        self.assertEqual(
            member_names(baseline.stdout),
            ["b/file"],
            "negative control: raw split must count the empty separator segment",
        )

        with tempfile.TemporaryDirectory(prefix="tarfilter-strip-empty-") as td:
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

            for index, (name, count) in enumerate(
                (
                    ("a//b/file", 1),
                    ("a//b/file", 2),
                    ("./a//b/file", 3),
                    ("a/b/file", 2),
                )
            ):
                archive = fixture_archive(name)
                reference_root = work / f"reference-{index}"
                reference_root.mkdir()
                expected = gnu_transformed_name(archive, count, reference_root)
                filtered = run_filter(candidate, archive, count)
                self.assertEqual(
                    filtered.returncode,
                    0,
                    filtered.stderr.decode("utf-8", errors="replace"),
                )
                self.assertEqual(member_names(filtered.stdout), [expected])

            omitted = fixture_archive("a///file")
            reference_root = work / "omitted"
            reference_root.mkdir()
            self.assertTrue(gnu_extracts_nothing(omitted, 2, reference_root))

            baseline_omitted = run_filter(source, omitted, 2)
            self.assertEqual(baseline_omitted.returncode, 0)
            self.assertEqual(member_names(baseline_omitted.stdout), ["/file"])

            candidate_omitted = run_filter(candidate, omitted, 2)
            self.assertEqual(
                candidate_omitted.returncode,
                0,
                candidate_omitted.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(member_names(candidate_omitted.stdout), [])


if __name__ == "__main__":
    unittest.main()
