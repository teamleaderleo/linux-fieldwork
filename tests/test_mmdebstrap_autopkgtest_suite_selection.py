import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream" / "mmdebstrap" / "debian" / "tests" / "testsuite"
PATCH = (
    ROOT
    / "investigations"
    / "mmdebstrap-autopkgtest-nondebian-skip"
    / "0001-skip-unsupported-apt-archives.patch"
)

FAKE_APT_PKG = r'''
import json
import os


def init():
    return None


class PackageFile:
    def __init__(self, data):
        self.priority = data.get("priority", 500)
        self.trusted = data.get("trusted", True)
        self.index_none = data.get("index_none", False)
        for name in (
            "architecture",
            "archive",
            "codename",
            "component",
            "filename",
            "id",
            "index_type",
            "label",
            "not_automatic",
            "not_source",
            "origin",
            "site",
            "size",
            "version",
        ):
            setattr(self, name, data.get(name))

    def __str__(self):
        return self.filename or self.archive or "fake-package-file"


class Cache:
    def __init__(self, _progress):
        data = json.loads(os.environ["FAKE_APT_FILES"])
        self.file_list = [PackageFile(item) for item in data]

    def __getitem__(self, name):
        if name != "base-files":
            raise KeyError(name)
        return object()


class CandidateVersion:
    def __init__(self, files):
        self.file_list = [(item, None) for item in files]


class Policy:
    @staticmethod
    def get_priority(package_file):
        return package_file.priority


class DepCache:
    def __init__(self, cache):
        self.cache = cache
        self.policy = Policy()

    def get_candidate_ver(self, _package):
        return CandidateVersion(self.cache.file_list)


class Index:
    def __init__(self, trusted):
        self.is_trusted = trusted

    def __str__(self):
        return "fake-index"


class SourceList:
    def read_main_list(self):
        return None

    @staticmethod
    def find_index(package_file):
        if package_file.index_none:
            return None
        return Index(package_file.trusted)
'''


def extract_selector(source_text):
    marker = "DEFAULT_DIST=$(cat << END | python3 -\n"
    start = source_text.index(marker) + len(marker)
    end = source_text.index("\nEND\n)", start)
    return source_text[start:end] + "\n"


class MmdebstrapAutopkgtestSuiteSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = pathlib.Path(tempfile.mkdtemp(prefix="mmdebstrap-suite-selection-"))
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.fake_module_dir = self.tempdir / "fake-module"
        self.fake_module_dir.mkdir()
        (self.fake_module_dir / "apt_pkg.py").write_text(FAKE_APT_PKG, encoding="utf-8")

    def apply_candidate_patch(self):
        tree = self.tempdir / "tree"
        destination = tree / "upstream" / "mmdebstrap" / "debian" / "tests"
        destination.mkdir(parents=True)
        shutil.copy2(SOURCE, destination / "testsuite")
        subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=tree,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return destination / "testsuite"

    def run_selector(self, source_path, files):
        selector = extract_selector(source_path.read_text(encoding="utf-8"))
        selector_path = self.tempdir / f"selector-{source_path.parent.name}.py"
        selector_path.write_text(selector, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.fake_module_dir)
        env["FAKE_APT_FILES"] = json.dumps(files)
        return subprocess.run(
            [sys.executable, str(selector_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_candidate_patch_applies_to_exact_imported_source(self):
        patched = self.apply_candidate_patch().read_text(encoding="utf-8")
        self.assertIn("\texit(77)\n", patched)
        self.assertNotIn("\texit(1)\nprint(\"highest archive priority", patched)

    def test_trusted_debian_archive_selection_is_unchanged(self):
        result = self.run_selector(
            self.apply_candidate_patch(),
            [
                {
                    "archive": "stable",
                    "priority": 500,
                    "trusted": True,
                    "filename": "stable_Packages",
                },
                {
                    "archive": "testing",
                    "priority": 900,
                    "trusted": True,
                    "filename": "testing_Packages",
                },
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "testing")
        self.assertIn("highest archive priority: testing", result.stderr)

    def test_untrusted_higher_priority_archive_is_ignored(self):
        result = self.run_selector(
            self.apply_candidate_patch(),
            [
                {
                    "archive": "unstable",
                    "priority": 1000,
                    "trusted": False,
                    "filename": "untrusted_Packages",
                },
                {
                    "archive": "stable",
                    "priority": 500,
                    "trusted": True,
                    "filename": "stable_Packages",
                },
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "stable")
        self.assertIn("is not trusted -- skipping", result.stderr)

    def test_old_source_hard_fails_but_candidate_neutrally_skips_nondebian_archive(self):
        files = [
            {
                "archive": "resolute",
                "codename": "resolute",
                "origin": "Ubuntu",
                "priority": 500,
                "trusted": True,
                "filename": "resolute_Packages",
            }
        ]
        baseline = self.run_selector(SOURCE, files)
        candidate = self.run_selector(self.apply_candidate_patch(), files)

        self.assertEqual(baseline.returncode, 1, baseline.stderr)
        self.assertEqual(candidate.returncode, 77, candidate.stderr)
        self.assertEqual(candidate.stdout, "")
        self.assertIn(
            "highest priority apt archive is neither stable, testing or unstable",
            candidate.stderr,
        )

    def test_set_e_command_substitution_preserves_neutral_status(self):
        files = [
            {
                "archive": "resolute",
                "priority": 500,
                "trusted": True,
                "filename": "resolute_Packages",
            }
        ]
        selector = extract_selector(
            self.apply_candidate_patch().read_text(encoding="utf-8")
        )
        selector_path = self.tempdir / "selector.py"
        selector_path.write_text(selector, encoding="utf-8")
        shell_script = textwrap.dedent(
            f"""\
            set -eu
            DEFAULT_DIST=$("{sys.executable}" "{selector_path}")
            printf 'unexpected continuation: %s\\n' "$DEFAULT_DIST"
            """
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.fake_module_dir)
        env["FAKE_APT_FILES"] = json.dumps(files)
        result = subprocess.run(
            ["/bin/sh", "-c", shell_script],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        self.assertEqual(result.returncode, 77, result.stderr)
        self.assertNotIn("unexpected continuation", result.stdout)


if __name__ == "__main__":
    unittest.main()
