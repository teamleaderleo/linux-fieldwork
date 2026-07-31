import pathlib
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = (
    REPO_ROOT / "investigations/mmdebstrap-unwritable-tmpdir/run.sh",
    REPO_ROOT / "investigations/mmdebstrap-unwritable-tmpdir/deep_review.sh",
)

LIFECYCLE_BLOCK = textwrap.dedent(
    """
    finish() {
      local primary_status=$1 cleanup_status=0
      trap - EXIT INT TERM
      cleanup || cleanup_status=$?
      if [[ $primary_status -ne 0 ]]; then
        exit "$primary_status"
      fi
      exit "$cleanup_status"
    }

    exit_cleanup() {
      finish "$?"
    }

    trap exit_cleanup EXIT
    trap 'finish 130' INT
    trap 'finish 143' TERM
    """
).strip()


class UnwritableTmpdirSignalCleanupTests(unittest.TestCase):
    def test_repository_harnesses_use_the_reviewed_lifecycle(self):
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                source = script.read_text(encoding="utf-8")
                self.assertEqual(source.count(LIFECYCLE_BLOCK), 1)
                self.assertNotIn("trap cleanup EXIT INT TERM", source)
                subprocess.run(["bash", "-n", str(script)], check=True)

    def _run_model(self, lifecycle, action, cleanup_status):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            log = root / "events.log"
            script = root / "model.sh"
            script.write_text(
                textwrap.dedent(
                    f"""
                    #!/usr/bin/env bash
                    set -u
                    log=$1
                    configured_cleanup_status=$2

                    cleanup() {{
                      printf 'cleanup\n' >>"$log"
                      return "$configured_cleanup_status"
                    }}

                    {lifecycle}

                    case {action!r} in
                      success) exit 0 ;;
                      primary-failure) exit 42 ;;
                      int)
                        kill -INT "$$"
                        printf 'later\n' >>"$log"
                        exit 0
                        ;;
                      term)
                        kill -TERM "$$"
                        printf 'later\n' >>"$log"
                        exit 0
                        ;;
                    esac
                    """
                ),
                encoding="utf-8",
            )
            script.chmod(0o755)
            completed = subprocess.run(
                ["bash", str(script), str(log), str(cleanup_status)],
                check=False,
                text=True,
                capture_output=True,
                timeout=5,
            )
            events = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
            return completed.returncode, events

    def test_baseline_cleanup_only_signal_trap_falls_through_and_reenters(self):
        baseline = "trap cleanup EXIT INT TERM"
        status, events = self._run_model(baseline, "term", 0)
        self.assertEqual(status, 0)
        self.assertEqual(events, ["cleanup", "later", "cleanup"])

    def test_candidate_preserves_primary_failure_over_cleanup_failure(self):
        status, events = self._run_model(LIFECYCLE_BLOCK, "primary-failure", 74)
        self.assertEqual(status, 42)
        self.assertEqual(events, ["cleanup"])

    def test_candidate_surfaces_cleanup_failure_after_success(self):
        status, events = self._run_model(LIFECYCLE_BLOCK, "success", 74)
        self.assertEqual(status, 74)
        self.assertEqual(events, ["cleanup"])

    def test_candidate_signals_terminate_once_without_later_work(self):
        for action, expected in (("int", 130), ("term", 143)):
            with self.subTest(action=action):
                status, events = self._run_model(LIFECYCLE_BLOCK, action, 74)
                self.assertEqual(status, expected)
                self.assertEqual(events, ["cleanup"])

    def test_candidate_immediate_clean_rerun(self):
        first_status, first_events = self._run_model(LIFECYCLE_BLOCK, "term", 0)
        second_status, second_events = self._run_model(LIFECYCLE_BLOCK, "success", 0)
        self.assertEqual((first_status, first_events), (143, ["cleanup"]))
        self.assertEqual((second_status, second_events), (0, ["cleanup"]))


if __name__ == "__main__":
    unittest.main()
