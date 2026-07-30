from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest


HARNESS_RELATIVE = pathlib.Path(
    "programmes/services-resources/lanes/"
    "LF-23-cancellation-subprocess-fd-cleanup/scouts/"
    "LF-SCOUT-PROC-01/artifacts/cancellation_harness.py"
)
PATCH_RELATIVE = HARNESS_RELATIVE.parent / "mmdebstrap-run-progress-record-signal.patch"


def load_harness(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("lf23_cancellation_harness", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LF23SignalRepairTest(unittest.TestCase):
    def test_parent_only_signal_fails_after_child_cleanup(self) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        harness = load_harness(repo / HARNESS_RELATIVE)

        with tempfile.TemporaryDirectory(prefix="lf23-signal-repair-") as td:
            work = pathlib.Path(td)
            candidate_repo = work / "candidate"
            upstream = candidate_repo / "upstream/mmdebstrap"
            upstream.mkdir(parents=True)
            candidate_source = upstream / "mmdebstrap"
            shutil.copy2(repo / "upstream/mmdebstrap/mmdebstrap", candidate_source)

            applied = subprocess.run(
                [
                    "patch",
                    "-p1",
                    "-d",
                    str(candidate_repo),
                    "-i",
                    str(repo / PATCH_RELATIVE),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

            instrumented_text = harness.instrument_source(candidate_source.read_text())
            driver = work / "mmdebstrap.run-progress-driver"
            driver.write_text(harness.make_run_progress_driver(instrumented_text))
            driver.chmod(0o755)

            result = harness.run_progress_parent_only(driver, work / "run")
            self.assertNotEqual(result["interrupted_exit"], 0)
            self.assertTrue(result["interruption_logged"])
            self.assertFalse(result["returned_success"])
            self.assertFalse(result["misreported_success"])
            self.assertEqual(result["after_exit"]["process_count"], 0)
            self.assertEqual(result["rerun_exit"], 0)
            self.assertEqual(result["rerun_after_exit"]["process_count"], 0)


if __name__ == "__main__":
    unittest.main()
