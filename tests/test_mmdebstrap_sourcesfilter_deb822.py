from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/debian/tests/sourcesfilter"
PATCH = ROOT / (
    "investigations/mmdebstrap-autopkgtest-1141078/"
    "sourcesfilter-deb822.patch"
)


class FakeDeb822SourceEntry:
    def __init__(self, typ: str, uri: str, comps: list[str]) -> None:
        self.type = typ
        self.uri = uri
        self.comps = comps
        self.file = "/etc/apt/sources.list.d/debian.sources"

    def str(self) -> str:
        return (
            f"Types: {self.type}\n"
            f"URIs: {self.uri}\n"
            "Suites: sid\n"
            f"Components: {' '.join(self.comps)}\n"
        )

    def __str__(self) -> str:
        return self.str().strip()


class FakeSourcesList:
    last_instance: "FakeSourcesList | None" = None

    def __init__(self, _with_matcher: bool, *, deb822: bool) -> None:
        if not deb822:
            raise AssertionError("test fixture requires deb822=True")
        self.exploded_called = False
        self.list = [
            FakeDeb822SourceEntry(
                "deb", "http://deb.debian.org/debian", ["main", "contrib"]
            ),
            FakeDeb822SourceEntry(
                "deb", "http://mirror.invalid/debian", ["main"]
            ),
            FakeDeb822SourceEntry(
                "deb-src", "http://deb.debian.org/debian", ["main"]
            ),
            FakeDeb822SourceEntry(
                "deb", "http://deb.debian.org/debian-debug", ["main"]
            ),
            FakeDeb822SourceEntry("deb", "file:///srv/repo", ["contrib"]),
        ]
        FakeSourcesList.last_instance = self

    def __iter__(self):
        return iter(self.list)

    def exploded_list(self):
        self.exploded_called = True
        return list(self.list)

    def remove(self, entry) -> None:
        self.list.remove(entry)

    def save(self) -> None:
        files: dict[pathlib.Path, list[str]] = {}
        for entry in self.list:
            files.setdefault(pathlib.Path(entry.file), []).append(entry.str())
        for path, paragraphs in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(paragraphs), encoding="utf-8")


def load_sourcesfilter(path: pathlib.Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise AssertionError("could not build import spec")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MmdebstrapSourcesfilterDeb822Test(unittest.TestCase):
    def fake_modules(self):
        package = types.ModuleType("aptsources")
        package.__path__ = []
        sourceslist = types.ModuleType("aptsources.sourceslist")
        sourceslist.SourcesList = FakeSourcesList
        sourceslist.Deb822SourceEntry = FakeDeb822SourceEntry
        package.sourceslist = sourceslist
        return mock.patch.dict(
            sys.modules,
            {
                "apt_pkg": types.ModuleType("apt_pkg"),
                "aptsources": package,
                "aptsources.sourceslist": sourceslist,
            },
        )

    def test_candidate_processes_deb822_entries_through_exploded_view(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mmdebstrap-sourcesfilter-") as td:
            work = pathlib.Path(td)
            baseline_root = work / "baseline-root"
            candidate_root = work / "candidate-root"

            with self.fake_modules():
                baseline = load_sourcesfilter(SOURCE, "sourcesfilter_baseline")
                with self.assertRaises(AssertionError):
                    baseline.main(str(baseline_root))

            candidate_tree = work / "candidate"
            candidate = candidate_tree / "debian/tests/sourcesfilter"
            candidate.parent.mkdir(parents=True)
            shutil.copy2(SOURCE, candidate)
            applied = subprocess.run(
                [
                    "patch",
                    "--batch",
                    "--forward",
                    "-p1",
                    "-d",
                    str(candidate_tree),
                    "-i",
                    str(PATCH),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            patched_text = candidate.read_text(encoding="utf-8")
            self.assertIn("sources.exploded_list()", patched_text)
            self.assertNotIn("assert not isinstance", patched_text)

            with self.fake_modules():
                fixed = load_sourcesfilter(candidate, "sourcesfilter_candidate")
                with mock.patch.object(fixed.glob, "glob", return_value=[]):
                    fixed.main(str(candidate_root))

            instance = FakeSourcesList.last_instance
            self.assertIsNotNone(instance)
            assert instance is not None
            self.assertTrue(instance.exploded_called)
            self.assertEqual(len(instance.list), 2)
            self.assertTrue(
                all(entry.file.startswith(str(candidate_root)) for entry in instance.list)
            )

            entries = {(entry.type, entry.uri, tuple(entry.comps)) for entry in instance.list}
            self.assertEqual(
                entries,
                {
                    ("deb", "http://127.0.0.1/debian", ("main",)),
                    ("deb", "file:///srv/repo", ("contrib",)),
                },
            )

            output = (
                candidate_root / "etc/apt/sources.list.d/debian.sources"
            ).read_text(encoding="utf-8")
            self.assertIn("URIs: http://127.0.0.1/debian", output)
            self.assertIn("URIs: file:///srv/repo", output)
            self.assertNotIn("deb-src", output)
            self.assertNotIn("debian-debug", output)


if __name__ == "__main__":
    unittest.main()
