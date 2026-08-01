#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("archive_boundary_process_probe.py")
SPEC = importlib.util.spec_from_file_location("archive_boundary_process_probe", SCRIPT)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


@unittest.skipUnless(sys.platform.startswith("linux") and Path("/proc").is_dir(), "Linux /proc required")
class ArchiveBoundaryProcessProbeTest(unittest.TestCase):
    def test_parse_proc_stat_handles_spaces_in_comm(self) -> None:
        rest = ["S", "1", "2", "3"] + ["0"] * 15 + ["987"]
        parsed = probe.parse_proc_stat("123 (helper with spaces) " + " ".join(rest))
        self.assertEqual(parsed, (123, "helper with spaces", "S", 1, 2, 3, 987))

    def test_live_descendant_with_root_references_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            held = root / "held"
            held.write_text("sentinel\n", encoding="utf-8")
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import os,sys,time; os.chdir(sys.argv[1]); f=open('held','rb'); print('ready', flush=True); time.sleep(30)",
                    str(root),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(self._terminate, child)
            self.assertEqual(child.stdout.readline().strip(), "ready")

            snapshot = probe.capture_snapshot(
                root=root,
                worker_pid=os.getpid(),
                phase="after-setup",
                probe_pid=os.getpid(),
            )
            self.assertIn(child.pid, snapshot["live_owned_candidates"])
            item = self._record(snapshot, child.pid)
            self.assertIn("descendant", item["reasons"])
            self.assertIn("temporary_root_reference", item["reasons"])
            self.assertTrue(item["direct_owned_evidence"])

    def test_zombie_descendant_is_classified_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            worker = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import os,time,warnings; warnings.filterwarnings('ignore', category=DeprecationWarning); child=os.fork(); "
                        "(os._exit(0) if child == 0 else None); "
                        "print(child, flush=True); time.sleep(30)"
                    ),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(self._terminate, worker)
            zombie_pid = int(worker.stdout.readline().strip())
            deadline = time.time() + 3
            while time.time() < deadline:
                stat_path = Path("/proc") / str(zombie_pid) / "stat"
                if stat_path.exists() and probe.parse_proc_stat(stat_path.read_text())[2] == "Z":
                    break
                time.sleep(0.02)
            snapshot = probe.capture_snapshot(
                root=root,
                worker_pid=worker.pid,
                phase="before-tar",
                probe_pid=os.getpid(),
            )
            self.assertIn(zombie_pid, snapshot["zombie_owned_candidates"])
            self.assertNotIn(zombie_pid, snapshot["live_owned_candidates"])

    def test_cli_excludes_probe_process_and_writes_atomic_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "root"
            root.mkdir()
            output = base / "receipts" / "after-setup.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--worker-pid",
                    str(os.getpid()),
                    "--phase",
                    "after-setup",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "linux-fieldwork.archive-boundary-process-probe.v1")
            self.assertEqual(payload["worker_pid"], os.getpid())
            self.assertIn(payload["probe_pid"], payload["excluded_pids"])
            self.assertFalse(any(item["pid"] == payload["probe_pid"] for item in payload["relevant_processes"]))
            self.assertFalse(list(output.parent.glob(".*.tmp")))

    @staticmethod
    def _record(snapshot: dict[str, object], pid: int) -> dict[str, object]:
        for item in snapshot["relevant_processes"]:
            if item["pid"] == pid:
                return item
        raise AssertionError(f"PID {pid} absent from relevant process records")

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
