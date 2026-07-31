from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest

from tests.test_make_mirror_update_cache_signal_ownership import (
    MakeMirrorUpdateCacheSignalOwnershipTest,
)


class MakeMirrorUpdateCacheSignalMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        MakeMirrorUpdateCacheSignalOwnershipTest.setUpClass()
        cls.helper = MakeMirrorUpdateCacheSignalOwnershipTest(methodName="runTest")

    def run_owner_with_signal(
        self,
        owner: pathlib.Path,
        sig: signal.Signals,
    ) -> tuple[subprocess.Popen[str], pathlib.Path]:
        runtime = owner.parent
        process = subprocess.Popen(
            ["/bin/sh", str(owner)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        self.helper.wait_for_file(runtime / "ready", process)
        worker_pid = int((runtime / "worker.pid").read_text().strip())
        proxy_pid = int((runtime / "proxy.pid").read_text().strip())
        os.kill(worker_pid, sig)
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and self.helper.process_exists(proxy_pid):
            time.sleep(0.01)
        self.assertFalse(
            self.helper.process_exists(proxy_pid),
            f"parent-owned proxy {proxy_pid} survived {sig.name}",
        )
        return process, runtime

    def test_int_quit_term_status_cleanup_proxy_and_rerun(self) -> None:
        cases = (
            (signal.SIGINT, 130),
            (signal.SIGQUIT, 131),
            (signal.SIGTERM, 143),
        )
        with tempfile.TemporaryDirectory(prefix="update-cache-signal-matrix-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.helper.prepare_candidate(root)
            blocks = self.helper.candidate_blocks(candidate)

            for sig, expected in cases:
                with self.subTest(signal=sig.name):
                    runtime = root / f"signal-{sig.name.lower()}"
                    owner = self.helper.write_scripts(runtime, blocks, mode="signal")
                    process, runtime = self.run_owner_with_signal(owner, sig)
                    self.assertEqual(process.returncode, expected)
                    self.assertFalse((runtime / "worker-after").exists())
                    self.assertFalse((runtime / "owner-after").exists())
                    self.assertFalse((runtime / "apt-state").exists())
                    self.assertEqual(
                        (runtime / "cleanup.log").read_text().splitlines(),
                        ["subshell-cleanup"],
                    )
                    self.assertEqual(
                        (runtime / "owner-cleanup.log").read_text().splitlines(),
                        ["owner-cleanup"],
                    )

                    rerun_runtime = root / f"rerun-{sig.name.lower()}"
                    rerun_owner = self.helper.write_scripts(
                        rerun_runtime,
                        blocks,
                        mode="success",
                    )
                    rerun, rerun_runtime, _worker_pid = self.helper.run_owner(
                        rerun_owner,
                        signaled=False,
                    )
                    self.assertEqual(rerun.returncode, 0)
                    self.assertTrue((rerun_runtime / "worker-after").exists())
                    self.assertTrue((rerun_runtime / "owner-after").exists())
                    self.assertFalse((rerun_runtime / "apt-state").exists())
                    self.assertEqual(
                        (rerun_runtime / "cleanup.log").read_text().splitlines(),
                        ["subshell-cleanup"],
                    )
                    self.assertEqual(
                        (rerun_runtime / "owner-cleanup.log").read_text().splitlines(),
                        ["owner-cleanup"],
                    )


if __name__ == "__main__":
    unittest.main()
