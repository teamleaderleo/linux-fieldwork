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
    payload = b"strip\n"
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        member = tarfile.TarInfo("./a/b/file")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def run_filter(
    tarfilter: pathlib.Path, source: bytes, value: int
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(tarfilter), f"--strip-components={value}"],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def archive_members(source: bytes) -> list[tuple[str, bytes]]:
    with tarfile.open(fileobj=io.BytesIO(source), mode="r:*") as archive:
        result = []
        for member in archive:
            extracted = archive.extractfile(member)
            result.append((member.name, extracted.read() if extracted else b""))
        return result


class LF14StripComponentsValidationTest(unittest.TestCase):
    def test_negative_values_are_rejected_like_gnu_tar(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        source_path = repo / "upstream/mmdebstrap/tarfilter"
        patch_path = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts/"
            "mmdebstrap-tarfilter-reject-negative-strip.patch"
        )
        source = fixture_archive()

        for value, expected_name in ((-1, "file"), (-2, "b/file")):
            with self.subTest(negative_control=value):
                baseline = run_filter(source_path, source, value)
                self.assertEqual(
                    baseline.returncode,
                    0,
                    baseline.stderr.decode("utf-8", errors="replace"),
                )
                self.assertEqual(
                    archive_members(baseline.stdout),
                    [(expected_name, b"strip\n")],
                    "negative control must reproduce Python reverse slicing",
                )

                reference = subprocess.run(
                    ["tar", "-tf", "-", f"--strip-components={value}"],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(reference.returncode, 0)

        with tempfile.TemporaryDirectory(prefix="lf14-strip-validation-") as td:
            candidate_repo = pathlib.Path(td) / "candidate"
            candidate = candidate_repo / "upstream/mmdebstrap/tarfilter"
            candidate.parent.mkdir(parents=True)
            shutil.copy2(source_path, candidate)
            applied = subprocess.run(
                ["patch", "-p1", "-d", str(candidate_repo), "-i", str(patch_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            for value in (-1, -2):
                with self.subTest(candidate=value):
                    completed = run_filter(candidate, source, value)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertEqual(completed.stdout, b"")
                    self.assertIn(b"must be non-negative", completed.stderr)

            zero = run_filter(candidate, source, 0)
            self.assertEqual(
                zero.returncode,
                0,
                zero.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(
                archive_members(zero.stdout),
                [("./a/b/file", b"strip\n")],
            )

            positive = run_filter(candidate, source, 1)
            self.assertEqual(
                positive.returncode,
                0,
                positive.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(
                archive_members(positive.stdout),
                [("a/b/file", b"strip\n")],
            )


if __name__ == "__main__":
    unittest.main()
