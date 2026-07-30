from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "investigations/lf-02-upgrade-failure-recovery/summarize.py"
PHASES = (
    "install-v1",
    "unpack-v2",
    "configure-v2",
    "unpack-v3-fail",
    "configure-v3-fail",
    "unpack-v3-recover",
    "configure-v3-recover",
    "purge",
)
CATEGORIES = (
    "required_host_read",
    "harmless_runtime_interaction",
    "unexpected_mutation",
    "service_action",
    "unresolved",
)
SNAPSHOTS = {
    "install-v1": (
        "installed",
        "1.0",
        {"etc/lf-lifecycle.conf": "default=one\n"},
    ),
    "local-edit": (
        "installed",
        "1.0",
        {"etc/lf-lifecycle.conf": "user=preserved\n"},
    ),
    "unpack-v2": (
        "unpacked",
        "2.0",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-new": "default=two\n",
        },
    ),
    "configure-v2": (
        "installed",
        "2.0",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-dist": "default=two\n",
        },
    ),
    "unpack-v3-fail": (
        "unpacked",
        "3.0",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-dist": "default=two\n",
            "etc/lf-lifecycle.conf.dpkg-new": "default=three\n",
        },
    ),
    "configure-v3-fail": (
        "half-configured",
        "3.0",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-dist": "default=three\n",
        },
    ),
    "unpack-v3-recover": (
        "unpacked",
        "3.1",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-dist": "default=three\n",
            "etc/lf-lifecycle.conf.dpkg-new": "default=three-recovered\n",
        },
    ),
    "configure-v3-recover": (
        "installed",
        "3.1",
        {
            "etc/lf-lifecycle.conf": "user=preserved\n",
            "etc/lf-lifecycle.conf.dpkg-dist": "default=three-recovered\n",
        },
    ),
    "purge": ("absent", None, {}),
}


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_results(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    results = root / "results"
    target = (root / "target").resolve()
    results.mkdir()
    target.mkdir()
    write_json(results / "provenance.json", {"schema_version": 1})
    write_json(results / "fixtures/manifest.json", {"schema_version": 1})

    for name in PHASES:
        deliberate_failure = name == "configure-v3-fail"
        write_json(
            results / f"{name}.phase.json",
            {
                "schema_version": 1,
                "name": name,
                "expected_exit": "nonzero" if deliberate_failure else "0",
                "exit_status": 1 if deliberate_failure else 0,
                "duration_ms": 1,
            },
        )
        categories = {identifier: 0 for identifier in CATEGORIES}
        write_json(
            results / f"{name}-access.summary.json",
            {
                "schema_version": 1,
                "categories": categories,
                "category_total_matches_events": True,
                "category_total": 0,
                "outside_access_events": 0,
            },
        )

    script_log = [
        f"phase=postinst script_version=3.0 dpkg_root={target} cwd={target}",
        f"phase=postinst script_version=3.1 dpkg_root={target} cwd={target}",
    ]
    for label, (status, payload, conffile_contents) in SNAPSHOTS.items():
        conffiles = {
            path: {"content": content, "size_bytes": len(content), "sha256": "test"}
            for path, content in conffile_contents.items()
        }
        write_json(
            results / f"{label}.snapshot.json",
            {
                "schema_version": 1,
                "package": {"status_word": status},
                "payload_version": payload,
                "conffiles": conffiles,
                "script_log": script_log if label == "purge" else [],
                "artifacts": {"tree": f"{label}-tree.tsv"},
            },
        )
    (results / "host-fingerprint.diff").write_text("", encoding="utf-8")
    return results, target


def run_summary(
    results: pathlib.Path, target: pathlib.Path, *, optimized: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(SCRIPT), "--results", str(results), "--target", str(target)])
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )


class LF02UpgradeFailureSummaryTest(unittest.TestCase):
    def mutate_json(
        self, path: pathlib.Path, mutator: Callable[[dict[str, object]], None]
    ) -> None:
        record = json.loads(path.read_text(encoding="utf-8"))
        mutator(record)
        write_json(path, record)

    def assert_rejected_in_both_modes(
        self, mutator: Callable[[pathlib.Path, pathlib.Path], None]
    ) -> None:
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as tmp:
                results, target = make_results(pathlib.Path(tmp))
                mutator(results, target)
                completed = run_summary(results, target, optimized=optimized)
                self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
                self.assertIn("evidence validation failed:", completed.stderr)
                self.assertFalse((results / "summary.json").exists())

    def test_invalid_evidence_is_rejected_with_and_without_optimization(self) -> None:
        mutations: dict[str, Callable[[pathlib.Path, pathlib.Path], None]] = {
            "phase-status": lambda results, target: self.mutate_json(
                results / "configure-v2.phase.json",
                lambda record: record.__setitem__("exit_status", 1),
            ),
            "snapshot-state": lambda results, target: self.mutate_json(
                results / "configure-v3-recover.snapshot.json",
                lambda record: record["package"].__setitem__("status_word", "half-configured"),
            ),
            "category-total": lambda results, target: self.mutate_json(
                results / "install-v1-access.summary.json",
                lambda record: record.__setitem__("category_total", 1),
            ),
            "script-root": lambda results, target: self.mutate_json(
                results / "purge.snapshot.json",
                lambda record: record.__setitem__(
                    "script_log",
                    [
                        "phase=postinst script_version=3.0 dpkg_root=/wrong cwd=/wrong",
                        "phase=postinst script_version=3.1 dpkg_root=/wrong cwd=/wrong",
                    ],
                ),
            ),
            "conffile-sibling": lambda results, target: self.mutate_json(
                results / "configure-v2.snapshot.json",
                lambda record: record["conffiles"].__setitem__(
                    "etc/lf-lifecycle.conf.dpkg-old",
                    {"content": "stale\n", "size_bytes": 6, "sha256": "test"},
                ),
            ),
        }
        for name, mutator in mutations.items():
            with self.subTest(mutation=name):
                self.assert_rejected_in_both_modes(mutator)

    def set_category(self, results: pathlib.Path, identifier: str, count: int) -> None:
        path = results / "install-v1-access.summary.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["categories"][identifier] = count
        record["category_total"] = count
        record["outside_access_events"] = count
        write_json(path, record)

    def test_disposition_precedence(self) -> None:
        cases = (
            ("clean", {}, "retain-mapped-behavior", False, False),
            ("service", {"service_action": 1}, "promote-product-candidate", True, False),
            ("mutation", {"unexpected_mutation": 1}, "promote-product-candidate", True, False),
            ("unresolved", {"unresolved": 1}, "blocked-unresolved", False, True),
            (
                "service-and-unresolved",
                {"service_action": 1, "unresolved": 1},
                "promote-product-candidate",
                True,
                False,
            ),
        )
        for name, categories, expected, product, blocked in cases:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                results, target = make_results(pathlib.Path(tmp))
                for identifier, count in categories.items():
                    self.set_category(results, identifier, count)
                completed = run_summary(results, target)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                summary = json.loads((results / "summary.json").read_text())
                self.assertEqual(summary["disposition"], expected)
                self.assertIs(summary["decision_inputs"]["product_candidate"], product)
                self.assertIs(summary["decision_inputs"]["blocked_unresolved"], blocked)

    def test_host_fingerprint_change_promotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, target = make_results(pathlib.Path(tmp))
            (results / "host-fingerprint.diff").write_text("changed\n", encoding="utf-8")
            completed = run_summary(results, target, optimized=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((results / "summary.json").read_text())
            self.assertEqual(summary["disposition"], "promote-product-candidate")
            self.assertIs(summary["decision_inputs"]["host_fingerprint_unchanged"], False)


if __name__ == "__main__":
    unittest.main()
