from __future__ import annotations

import os
import pathlib
import signal
import stat
import subprocess
import tempfile
import time
import unittest


CANDIDATE = r'''#!/bin/sh
set -eu
die() { echo "$*" >&2; exit 1; }
WORKDIR=
IMAGE_TMPDIR=
IMAGE_TMP=
prepare_image() {
  case $IMAGE in
    */) die "invalid image path: $IMAGE" ;;
  esac
  image_parent=$(realpath -e -- "$(dirname -- "$IMAGE")") \
    || die "cannot resolve image parent for $IMAGE"
  test "$image_parent" != / \
    || die "refusing to build an image directly below /: $IMAGE"
  image_name=$(basename -- "$IMAGE")
  case $image_name in
    "" | . | .. | /) die "invalid image path: $IMAGE" ;;
  esac
  IMAGE="$image_parent/$image_name"
  IMAGE_TMPDIR=$(mktemp -d --tmpdir="$image_parent" \
    ".$image_name.mmdebstrap.XXXXXXXXXX")
  IMAGE_TMP="$IMAGE_TMPDIR/image"
}
publish_image() {
  mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"
  IMAGE_TMP=
  published_image_tmpdir=$IMAGE_TMPDIR
  if ! rmdir -- "$published_image_tmpdir"; then
    echo "W: image published but private directory remains: $published_image_tmpdir" >&2
  fi
  IMAGE_TMPDIR=
}
cleanup() {
  cleanup_status=0
  if test -n "$WORKDIR"; then
    rm -Rf -- "$WORKDIR" || cleanup_status=$?
    WORKDIR=
  fi
  if test -n "${IMAGE_TMPDIR:-}"; then
    if test -n "${IMAGE_TMP:-}"; then
      rm -f -- "$IMAGE_TMP" || cleanup_status=$?
    fi
    rmdir -- "$IMAGE_TMPDIR" 2>/dev/null || cleanup_status=$?
    IMAGE_TMP=
    IMAGE_TMPDIR=
  fi
  return "$cleanup_status"
}
exit_cleanup() {
  status=$?
  trap - EXIT HUP INT QUIT TERM
  cleanup_status=0
  cleanup || cleanup_status=$?
  if test "$status" -eq 0 && test "$cleanup_status" -ne 0; then
    status=$cleanup_status
  fi
  exit "$status"
}
signal_exit() {
  status=$1
  trap - EXIT HUP INT QUIT TERM
  cleanup || :
  exit "$status"
}
trap exit_cleanup EXIT
trap 'signal_exit 129' HUP
trap 'signal_exit 130' INT
trap 'signal_exit 131' QUIT
trap 'signal_exit 143' TERM
RUNTIME=$1
MODE=$2
IMAGE=$3
WORKDIR=$RUNTIME/work
mkdir "$WORKDIR"
prepare_image
umask 022
printf partial >"$IMAGE_TMP"
case "$MODE" in
  failure) exit 42 ;;
  success) printf complete >"$IMAGE_TMP"; publish_image ;;
  wait-before)
    printf ready >"$RUNTIME/ready"
    sleep 0.4
    printf complete >"$IMAGE_TMP"
    publish_image
    ;;
  wait-after)
    printf complete >"$IMAGE_TMP"
    publish_image
    printf ready >"$RUNTIME/ready"
    sleep 0.4
    ;;
esac
printf after >"$RUNTIME/after"
'''

BASELINE = r'''#!/bin/sh
set -eu
RUNTIME=$1
WORKDIR=$RUNTIME/work
mkdir "$WORKDIR"
cleanup() {
  test -n "$WORKDIR" && rm -Rf "$WORKDIR"
}
trap cleanup EXIT INT TERM QUIT
printf ready >"$RUNTIME/ready"
sleep 0.4
printf after >"$RUNTIME/after"
'''


class LifecycleModelTest(unittest.TestCase):
    def write_script(self, root: pathlib.Path, name: str, content: str) -> pathlib.Path:
        script = root / name
        script.write_text(content, encoding="utf-8")
        checked = subprocess.run(
            ["sh", "-n", str(script)], capture_output=True, text=True, check=False
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return script

    def execute_candidate(
        self,
        script: pathlib.Path,
        runtime: pathlib.Path,
        mode: str,
        image: pathlib.Path | str,
    ) -> subprocess.CompletedProcess[str]:
        runtime.mkdir()
        return subprocess.run(
            ["sh", str(script), str(runtime), mode, str(image)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def execute_signaled(
        self,
        argv: list[str],
        runtime: pathlib.Path,
        sig: signal.Signals,
    ) -> subprocess.CompletedProcess[str]:
        runtime.mkdir()
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        ready = runtime / "ready"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not ready.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"script exited before ready: {process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        self.assertTrue(ready.exists(), "script did not become ready")
        os.kill(process.pid, sig)
        stdout, stderr = process.communicate(timeout=10)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    @staticmethod
    def private_dirs(image: pathlib.Path) -> list[pathlib.Path]:
        return list(image.parent.glob(f".{image.name}.mmdebstrap.*"))

    def test_baseline_term_resumes_but_candidate_terminates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unit04-baseline-") as tmp:
            root = pathlib.Path(tmp)
            baseline = self.write_script(root, "baseline.sh", BASELINE)
            baseline_runtime = root / "baseline"
            baseline_result = self.execute_signaled(
                ["sh", str(baseline), str(baseline_runtime)],
                baseline_runtime,
                signal.SIGTERM,
            )
            self.assertEqual(baseline_result.returncode, 0)
            self.assertTrue((baseline_runtime / "after").exists())

            candidate = self.write_script(root, "candidate.sh", CANDIDATE)
            image = root / "candidate.img"
            image.write_bytes(b"sentinel")
            runtime = root / "candidate"
            candidate_result = self.execute_signaled(
                ["sh", str(candidate), str(runtime), "wait-before", str(image)],
                runtime,
                signal.SIGTERM,
            )
            self.assertEqual(candidate_result.returncode, 143)
            self.assertFalse((runtime / "after").exists())
            self.assertEqual(image.read_bytes(), b"sentinel")
            self.assertEqual(self.private_dirs(image), [])

    def test_failure_success_and_late_signal_publication(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unit04-publication-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.write_script(root, "candidate.sh", CANDIDATE)

            existing = root / "existing.img"
            existing.write_bytes(b"sentinel")
            existing.chmod(0o600)
            failed = self.execute_candidate(
                candidate, root / "failure", "failure", existing
            )
            self.assertEqual(failed.returncode, 42)
            self.assertEqual(existing.read_bytes(), b"sentinel")
            self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o600)
            self.assertEqual(self.private_dirs(existing), [])

            published = root / "published.img"
            published.write_bytes(b"sentinel")
            succeeded = self.execute_candidate(
                candidate, root / "success", "success", published
            )
            self.assertEqual(succeeded.returncode, 0)
            self.assertEqual(published.read_bytes(), b"complete")
            self.assertEqual(stat.S_IMODE(published.stat().st_mode), 0o644)
            self.assertEqual(self.private_dirs(published), [])

            late = root / "late.img"
            late.write_bytes(b"sentinel")
            late_runtime = root / "late"
            signaled = self.execute_signaled(
                ["sh", str(candidate), str(late_runtime), "wait-after", str(late)],
                late_runtime,
                signal.SIGTERM,
            )
            self.assertEqual(signaled.returncode, 143)
            self.assertEqual(late.read_bytes(), b"complete")
            self.assertFalse((late_runtime / "after").exists())
            self.assertEqual(self.private_dirs(late), [])

    def test_trailing_slash_rejected_before_private_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unit04-path-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.write_script(root, "candidate.sh", CANDIDATE)
            destination = root / "existing"
            destination.mkdir()
            completed = self.execute_candidate(
                candidate,
                root / "trailing",
                "failure",
                f"{destination}/",
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("invalid image path", completed.stderr)
            self.assertEqual(self.private_dirs(destination), [])
            self.assertFalse((destination / destination.name).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
