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
        payload = b"base\n"
        base = tarfile.TarInfo("prefix/base")
        base.size = len(payload)
        archive.addfile(base, io.BytesIO(payload))

        sym = tarfile.TarInfo("prefix/sym")
        sym.type = tarfile.SYMTYPE
        sym.linkname = "prefix/target"
        archive.addfile(sym)

        hard = tarfile.TarInfo("prefix/hard")
        hard.type = tarfile.LNKTYPE
        hard.linkname = "prefix/base"
        archive.addfile(hard)
    return output.getvalue()


def inspect_archive(archive: bytes) -> dict[str, tuple[str, str]]:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
        return {
            member.name: (
                "sym" if member.issym() else "hard" if member.islnk() else "file",
                member.linkname,
            )
            for member in handle
        }


class LF14TransformLinkScopesTest(unittest.TestCase):
    def test_default_and_opt_out_scopes_match_gnu_tar(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        lane = repo / (
            "programmes/filesystems-images/lanes/"
            "LF-14-archive-extraction-metadata-contracts/scouts/"
            "LF-SCOUT-FS-01/artifacts"
        )

        with tempfile.TemporaryDirectory(prefix="lf14-transform-scopes-") as td:
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

            source = fixture_archive()
            tarfilter = upstream / "tarfilter"
            cases = {
                "s,^prefix/, ,".replace(" ", ""): {
                    "base": ("file", ""),
                    "sym": ("sym", "target"),
                    "hard": ("hard", "base"),
                },
                "s,^prefix/,,S": {
                    "base": ("file", ""),
                    "sym": ("sym", "prefix/target"),
                    "hard": ("hard", "base"),
                },
                "s,^prefix/,,H": {
                    "base": ("file", ""),
                    "sym": ("sym", "target"),
                    "hard": ("hard", "prefix/base"),
                },
                "s,^prefix/,,R": {
                    "prefix/base": ("file", ""),
                    "prefix/sym": ("sym", "target"),
                    "prefix/hard": ("hard", "base"),
                },
            }

            for expression, expected in cases.items():
                reference = subprocess.run(
                    [
                        "tar",
                        "-tvf",
                        "-",
                        "--show-transformed-names",
                        f"--transform={expression}",
                    ],
                    input=source,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(reference.returncode, 0, reference.stderr)
                listing = reference.stdout
                for name, (kind, target) in expected.items():
                    self.assertIn(name, listing)
                    if kind == "sym":
                        self.assertIn(f"{name} -> {target}", listing)
                    elif kind == "hard":
                        self.assertIn(f"{name} link to {target}", listing)

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
                self.assertEqual(inspect_archive(filtered.stdout), expected)


if __name__ == "__main__":
    unittest.main()
