from __future__ import annotations

import importlib.util
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/probe_process_group_kill.py"
PATCH = ROOT / (
    "investigations/process-group-kill-syntax/"
    "0001-require-zero-command-status.patch"
)


class ProcessGroupKillZeroStatusSelectionTest(unittest.TestCase):
    def load_candidate(self, root: pathlib.Path):
        destination = root / "tools/probe_process_group_kill.py"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "--fuzz=0",
                "-p1",
                "-i",
                str(PATCH),
            ],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertNotIn("fuzz", (applied.stdout + applied.stderr).lower())

        spec = importlib.util.spec_from_file_location(
            f"probe_process_group_kill_candidate_{id(root)}",
            destination,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def result(
        module,
        name: str,
        *,
        classification: str,
        returncode: int = 0,
        parent_running: bool = False,
        child_running: bool = False,
        unrelated_running: bool = True,
    ):
        if classification == "owner-only-delivery":
            parent_signal = signal.SIGINT
            child_signal = None
        elif classification == "whole-group-delivery":
            parent_signal = signal.SIGINT
            child_signal = signal.SIGINT
        else:
            parent_signal = None
            child_signal = None
        return module.CaseResult(
            name=name,
            command=("synthetic", name),
            returncode=returncode,
            stdout="",
            stderr="" if returncode == 0 else "synthetic nonzero",
            parent_signal=parent_signal,
            child_signal=child_signal,
            unrelated_signal=None,
            parent_running=parent_running,
            child_running=child_running,
            unrelated_running=unrelated_running,
            classification=classification,
        )

    def install_synthetic_cases(
        self,
        module,
        *,
        dash_status: int,
        external_short_status: int,
        owner_status: int = 0,
        python_status: int = 0,
    ) -> None:
        names = (
            "owner-only-external",
            "external-long",
            "external-short",
            "external-compact",
            "dash-builtin-short",
        )
        module.command_cases = lambda: tuple(
            (name, (lambda parent, pgid, value=name: (value,))) for name in names
        )
        cases = {
            "owner-only-external": self.result(
                module,
                "owner-only-external",
                classification="owner-only-delivery",
                returncode=owner_status,
                child_running=True,
            ),
            "external-long": self.result(
                module,
                "external-long",
                classification="parser-or-target-rejection",
                returncode=1,
            ),
            "external-short": self.result(
                module,
                "external-short",
                classification="whole-group-delivery",
                returncode=external_short_status,
            ),
            "external-compact": self.result(
                module,
                "external-compact",
                classification="parser-or-target-rejection",
                returncode=1,
            ),
            "dash-builtin-short": self.result(
                module,
                "dash-builtin-short",
                classification="whole-group-delivery",
                returncode=dash_status,
            ),
            "python-killpg-control": self.result(
                module,
                "python-killpg-control",
                classification="whole-group-delivery",
                returncode=python_status,
            ),
        }

        def fake_run_case(name, builder, *, python_group_control=False):
            if python_group_control:
                return cases["python-killpg-control"]
            return cases[name]

        module.run_case = fake_run_case
        module.version_output = lambda command: "synthetic-version"

    def test_nonzero_delivery_is_visible_but_not_selected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kill-zero-status-selection-") as td:
            module = self.load_candidate(pathlib.Path(td))
            self.install_synthetic_cases(
                module,
                dash_status=1,
                external_short_status=0,
            )
            record = module.run_probe()

        self.assertEqual(record["selected_candidate"], "external-short")
        by_name = {item["name"]: item for item in record["results"]}
        self.assertEqual(
            by_name["dash-builtin-short"]["classification"],
            "whole-group-delivery",
        )
        self.assertEqual(by_name["dash-builtin-short"]["returncode"], 1)

    def test_all_nonzero_delivery_candidates_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kill-zero-status-none-") as td:
            module = self.load_candidate(pathlib.Path(td))
            self.install_synthetic_cases(
                module,
                dash_status=1,
                external_short_status=1,
            )
            with self.assertRaisesRegex(
                module.ProbeError,
                "no tested kill spelling delivered SIGINT to the whole group",
            ):
                module.run_probe()

    def test_control_statuses_are_authoritative(self) -> None:
        for label, owner_status, python_status, message in (
            ("owner", 1, 0, "owner-only negative control returned nonzero"),
            ("python", 0, 1, "Python killpg positive control returned nonzero"),
        ):
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory(
                    prefix=f"kill-zero-status-control-{label}-"
                ) as td:
                    module = self.load_candidate(pathlib.Path(td))
                    self.install_synthetic_cases(
                        module,
                        dash_status=0,
                        external_short_status=0,
                        owner_status=owner_status,
                        python_status=python_status,
                    )
                    with self.assertRaisesRegex(module.ProbeError, message):
                        module.run_probe()


if __name__ == "__main__":
    unittest.main()
