from __future__ import annotations

import pathlib
import signal
import subprocess
import tempfile
import unittest

from tests import test_make_mirror_update_cache_cleanup_signals as cleanup_signals


class MakeMirrorUpdateCacheCleanupSignalsRerunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cleanup_signals.MakeMirrorUpdateCacheCleanupSignalsTest.setUpClass()

    @staticmethod
    def run_unsignaled_cleanup(
        helper: cleanup_signals.MakeMirrorUpdateCacheCleanupSignalsTest,
        script: pathlib.Path,
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            ["/bin/sh", str(script)],
            cwd=script.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        helper.wait_for_file(script.parent / "cleanup-ready", process)
        (script.parent / "cleanup-release").touch()
        stdout, stderr = process.communicate(timeout=5)
        return subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout,
            stderr,
        )

    def test_cleanup_time_signal_allows_immediate_clean_rerun(self) -> None:
        helper = cleanup_signals.MakeMirrorUpdateCacheCleanupSignalsTest(
            methodName="runTest"
        )
        with tempfile.TemporaryDirectory(
            prefix="update-cache-cleanup-signal-rerun-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = helper.prepare_candidate(root, include_repair=True)

            signaled = helper.write_case(
                root,
                "signaled",
                source,
                mode="ordinary",
            )
            signaled_result = helper.run_signals_during_cleanup(
                signaled,
                first_signal=signal.SIGTERM,
                second_signal=signal.SIGINT,
                first_starts_cleanup=False,
            )
            self.assertEqual(signaled_result.returncode, 143, signaled_result.stderr)
            self.assertEqual(helper.cleanup_log(signaled.parent), ["start", "end"])
            self.assertFalse((signaled.parent / "apt-state").exists())
            self.assertFalse((signaled.parent / "later").exists())

            rerun = helper.write_case(
                root,
                "rerun",
                source,
                mode="ordinary",
            )
            rerun_result = self.run_unsignaled_cleanup(helper, rerun)
            self.assertEqual(rerun_result.returncode, 0, rerun_result.stderr)
            self.assertEqual(helper.cleanup_log(rerun.parent), ["start", "end"])
            self.assertFalse((rerun.parent / "apt-state").exists())
            self.assertFalse((rerun.parent / "later").exists())

    def test_explicit_signal_remains_ahead_of_cleanup_failure(self) -> None:
        helper = cleanup_signals.MakeMirrorUpdateCacheCleanupSignalsTest(
            methodName="runTest"
        )
        with tempfile.TemporaryDirectory(
            prefix="update-cache-explicit-signal-cleanup-failure-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = helper.prepare_candidate(root, include_repair=True)
            script = helper.write_case(
                root,
                "explicit-signal-cleanup-failure",
                source,
                mode="explicit",
                cleanup_failure=True,
            )
            result = helper.run_signals_during_cleanup(
                script,
                first_signal=signal.SIGTERM,
                second_signal=signal.SIGINT,
                first_starts_cleanup=True,
            )
            self.assertEqual(result.returncode, 143, result.stderr)
            self.assertEqual(helper.cleanup_log(script.parent), ["start", "end"])
            self.assertFalse((script.parent / "apt-state").exists())
            self.assertFalse((script.parent / "later").exists())

    def test_unsignaled_cleanup_failure_remains_authoritative(self) -> None:
        helper = cleanup_signals.MakeMirrorUpdateCacheCleanupSignalsTest(
            methodName="runTest"
        )
        with tempfile.TemporaryDirectory(
            prefix="update-cache-unsignaled-cleanup-failure-"
        ) as temporary:
            root = pathlib.Path(temporary)
            source = helper.prepare_candidate(root, include_repair=True)
            script = helper.write_case(
                root,
                "unsignaled-cleanup-failure",
                source,
                mode="ordinary",
                cleanup_failure=True,
            )
            result = self.run_unsignaled_cleanup(helper, script)
            self.assertEqual(result.returncode, 74, result.stderr)
            self.assertEqual(helper.cleanup_log(script.parent), ["start", "end"])
            self.assertFalse((script.parent / "apt-state").exists())
            self.assertFalse((script.parent / "later").exists())


if __name__ == "__main__":
    unittest.main()
