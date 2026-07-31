from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


class TarfilterTypeExcludedHardlinkCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/tarfilter"
        cls.integrated_patch = cls.repo / (
            "investigations/tarfilter-transform-target-scopes/"
            "tarfilter-transform-target-scopes.patch"
        )
        cls.candidate_patch = cls.repo / (
            "investigations/tarfilter-type-excluded-hardlink-target/"
            "0001-reject-hardlinks-to-type-excluded-members.patch"
        )
        if shutil.which("patch") is None or shutil.which("tar") is None:
            raise unittest.SkipTest("patch and GNU tar are required")

    @staticmethod
    def apply_patch(root: pathlib.Path, patch: pathlib.Path) -> None:
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)

    def prepare_candidate(self, root: pathlib.Path) -> pathlib.Path:
        tree = root / "candidate"
        destination = tree / "upstream/mmdebstrap/tarfilter"
        destination.parent.mkdir(parents=True)
        shutil.copy2(self.source, destination)
        self.apply_patch(tree, self.integrated_patch)
        self.apply_patch(tree, self.candidate_patch)
        compiled = subprocess.run(
            [sys.executable, "-m", "py_compile", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
        return destination

    @staticmethod
    def archive_bytes(*names: str, link_target: str = "root/base") -> bytes:
        output = io.BytesIO()
        payload = b"hard-link-payload\n"
        with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name in names:
                if name == "base":
                    member = tarfile.TarInfo("root/base")
                    member.size = len(payload)
                    member.mtime = 946684800
                    archive.addfile(member, io.BytesIO(payload))
                elif name in {"peer", "peer2"}:
                    member = tarfile.TarInfo(f"root/{name}")
                    member.type = tarfile.LNKTYPE
                    member.linkname = link_target
                    member.mtime = 946684800
                    archive.addfile(member)
                else:
                    raise AssertionError(f"unknown fixture member: {name}")
        return output.getvalue()

    @staticmethod
    def run_filter(
        source: pathlib.Path, archive: bytes, *options: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(source), *options],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    @staticmethod
    def member_map(archive: bytes) -> dict[str, tuple[bytes, str]]:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as handle:
            return {
                member.name: (member.type, member.linkname)
                for member in handle
            }

    @staticmethod
    def extract(
        archive: bytes, root: pathlib.Path, label: str
    ) -> tuple[subprocess.CompletedProcess[str], pathlib.Path]:
        archive_path = root / f"{label}.tar"
        destination = root / label
        archive_path.write_bytes(archive)
        destination.mkdir()
        completed = subprocess.run(
            ["tar", "-xf", str(archive_path), "-C", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return completed, destination

    def test_candidate_rejects_dangling_type_filtered_hardlink(self) -> None:
        archive = self.archive_bytes("base", "peer")
        with tempfile.TemporaryDirectory(prefix="tarfilter-type-candidate-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)

            baseline = self.run_filter(self.source, archive, "--type-exclude=REGTYPE")
            self.assertEqual(
                baseline.returncode,
                0,
                baseline.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(baseline.stdout),
                {"root/peer": (tarfile.LNKTYPE, "root/base")},
            )
            extracted, _ = self.extract(baseline.stdout, root, "baseline")
            self.assertNotEqual(extracted.returncode, 0)

            repaired = self.run_filter(candidate, archive, "--type-exclude=REGTYPE")
            self.assertEqual(repaired.returncode, 1)
            diagnostic = repaired.stderr.decode("utf-8", "replace")
            self.assertIn(
                "hard-link target excluded by type filter: root/peer -> root/base",
                diagnostic,
            )
            self.assertEqual(self.member_map(repaired.stdout), {})
            extracted, destination = self.extract(repaired.stdout, root, "repaired")
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            self.assertEqual(list(destination.rglob("*")), [])

    def test_candidate_matches_gnu_tar_leading_prefix_equivalence(self) -> None:
        equivalent_targets = (
            "./root/base",
            "/root/base",
            "../root/base",
            "../../root/base",
            ".//root/base",
            "//root/base",
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-type-normalize-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)
            for index, target in enumerate(equivalent_targets):
                with self.subTest(target=target):
                    archive = self.archive_bytes("base", "peer", link_target=target)
                    direct, direct_root = self.extract(
                        archive,
                        root,
                        f"direct-{index}",
                    )
                    self.assertEqual(
                        direct.returncode,
                        0,
                        direct.stdout + direct.stderr,
                    )
                    self.assertEqual(
                        (direct_root / "root/peer").read_bytes(),
                        b"hard-link-payload\n",
                    )

                    repaired = self.run_filter(
                        candidate,
                        archive,
                        "--type-exclude=REGTYPE",
                    )
                    self.assertEqual(repaired.returncode, 1)
                    diagnostic = repaired.stderr.decode("utf-8", "replace")
                    self.assertIn(f"root/peer -> {target}", diagnostic)
                    self.assertEqual(self.member_map(repaired.stdout), {})

    def test_candidate_does_not_invent_dot_prefix_equivalence(self) -> None:
        archive = self.archive_bytes(
            "base",
            "peer",
            link_target=".../root/base",
        )
        with tempfile.TemporaryDirectory(prefix="tarfilter-type-distinct-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)

            direct, _ = self.extract(archive, root, "direct")
            self.assertNotEqual(direct.returncode, 0)

            filtered = self.run_filter(
                candidate,
                archive,
                "--type-exclude=REGTYPE",
            )
            self.assertEqual(
                filtered.returncode,
                0,
                filtered.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(filtered.stdout),
                {"root/peer": (tarfile.LNKTYPE, ".../root/base")},
            )

    def test_candidate_preserves_independent_type_filters_and_rerun(self) -> None:
        archive = self.archive_bytes("base", "peer")
        with tempfile.TemporaryDirectory(prefix="tarfilter-type-rerun-") as td:
            root = pathlib.Path(td)
            candidate = self.prepare_candidate(root)

            hardlinks_removed = self.run_filter(
                candidate,
                archive,
                "--type-exclude=LNKTYPE",
                "--transform=s,^root/,,",
            )
            self.assertEqual(
                hardlinks_removed.returncode,
                0,
                hardlinks_removed.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                self.member_map(hardlinks_removed.stdout),
                {"base": (tarfile.REGTYPE, "")},
            )
            extracted, destination = self.extract(
                hardlinks_removed.stdout, root, "hardlinks-removed"
            )
            self.assertEqual(extracted.returncode, 0, extracted.stdout + extracted.stderr)
            self.assertEqual(
                (destination / "base").read_bytes(),
                b"hard-link-payload\n",
            )

            all_removed = self.run_filter(
                candidate,
                archive,
                "--type-exclude=REGTYPE",
                "--type-exclude=LNKTYPE",
            )
            self.assertEqual(
                all_removed.returncode,
                0,
                all_removed.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(self.member_map(all_removed.stdout), {})

    def test_candidate_rejects_first_of_multiple_retained_peers(self) -> None:
        archive = self.archive_bytes("base", "peer", "peer2")
        with tempfile.TemporaryDirectory(prefix="tarfilter-type-peers-") as td:
            candidate = self.prepare_candidate(pathlib.Path(td))
            completed = self.run_filter(
                candidate,
                archive,
                "--type-exclude=REGTYPE",
            )
            self.assertEqual(completed.returncode, 1)
            diagnostic = completed.stderr.decode("utf-8", "replace")
            self.assertIn("root/peer -> root/base", diagnostic)
            self.assertNotIn("root/peer2 -> root/base", diagnostic)
            self.assertEqual(self.member_map(completed.stdout), {})


if __name__ == "__main__":
    unittest.main()
