from __future__ import annotations

import os
import pathlib
import re
import signal
import stat
import subprocess
import tempfile
import time
import unittest


class QemuBuilderComposedLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        cls.patch = cls.repo / (
            "investigations/qemu-builder-composed-lifecycle/"
            "0001-compose-image-publication-and-signal-lifecycle.patch"
        )

    @staticmethod
    def extract_function(source: str, name: str) -> str:
        start = source.index(f"{name}() {{\n")
        end = source.index("\n}\n", start) + 3
        return source[start:end]

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        destination = tree / (
            "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"
        )
        destination.parent.mkdir(parents=True)
        destination.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(self.patch)],
            cwd=tree,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        checked = subprocess.run(
            ["sh", "-n", str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return destination.read_text(encoding="utf-8")

    def lifecycle_parts(self, source: str) -> tuple[str, str]:
        functions = "\n".join(
            self.extract_function(source, name)
            for name in (
                "prepare_image",
                "publish_image",
                "cleanup",
                "exit_cleanup",
                "signal_exit",
            )
        )
        start = source.index("trap exit_cleanup EXIT")
        end = source.index("\n\nWORKDIR=$(mktemp -d)", start)
        traps = source[start:end] + "\n"
        return functions, traps

    def write_lifecycle_harness(
        self, root: pathlib.Path, candidate: str
    ) -> pathlib.Path:
        functions, traps = self.lifecycle_parts(candidate)
        functions = functions.replace("cleanup() {", "product_cleanup() {", 1)
        script = root / "lifecycle-harness.sh"
        script.write_text(
            "#!/bin/sh\n"
            "set -eu\n"
            "die() { echo \"$*\" >&2; exit 1; }\n"
            "WORKDIR=\n"
            "IMAGE_TMPDIR=\n"
            "IMAGE_TMP=\n"
            "IN_CLEANUP=0\n"
            "FAIL_CLEANUP=${FAIL_CLEANUP:-0}\n"
            "rm() {\n"
            "  if test \"$IN_CLEANUP\" -eq 1 && test \"$FAIL_CLEANUP\" -eq 1; then\n"
            "    return 73\n"
            "  fi\n"
            "  command rm \"$@\"\n"
            "}\n"
            "rmdir() {\n"
            "  if test \"$IN_CLEANUP\" -eq 1 && test \"$FAIL_CLEANUP\" -eq 1; then\n"
            "    return 74\n"
            "  fi\n"
            "  command rmdir \"$@\"\n"
            "}\n"
            + functions
            + "\ncleanup() {\n"
            "  printf 'cleanup\\n' >>\"$CLEANUP_LOG\"\n"
            "  IN_CLEANUP=1\n"
            "  cleanup_result=0\n"
            "  product_cleanup || cleanup_result=$?\n"
            "  IN_CLEANUP=0\n"
            "  return \"$cleanup_result\"\n"
            "}\n"
            + traps
            + "RUNTIME=$1\n"
            "MODE=$2\n"
            "IMAGE=$3\n"
            "CLEANUP_LOG=$RUNTIME/cleanup.log\n"
            "WORKDIR=$RUNTIME/work\n"
            "mkdir \"$WORKDIR\"\n"
            "printf 'owned\\n' >\"$WORKDIR/owned\"\n"
            "prepare_image\n"
            "umask 022\n"
            "printf 'partial\\n' >\"$IMAGE_TMP\"\n"
            "case $MODE in\n"
            "  failure) exit 42 ;;\n"
            "  wait-before-publication)\n"
            "    printf 'ready\\n' >\"$RUNTIME/ready\"\n"
            "    sleep 0.4\n"
            "    printf 'complete\\n' >\"$IMAGE_TMP\"\n"
            "    publish_image\n"
            "    ;;\n"
            "  success)\n"
            "    printf 'complete\\n' >\"$IMAGE_TMP\"\n"
            "    publish_image\n"
            "    ;;\n"
            "  wait-after-publication)\n"
            "    printf 'complete\\n' >\"$IMAGE_TMP\"\n"
            "    publish_image\n"
            "    printf 'ready\\n' >\"$RUNTIME/ready\"\n"
            "    sleep 0.4\n"
            "    ;;\n"
            "  cleanup-only-success) : ;;\n"
            "  *) die \"unknown mode: $MODE\" ;;\n"
            "esac\n"
            "printf 'after\\n' >\"$RUNTIME/after\"\n",
            encoding="utf-8",
        )
        checked = subprocess.run(
            ["sh", "-n", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return script

    def run_harness(
        self,
        script: pathlib.Path,
        runtime: pathlib.Path,
        mode: str,
        image: pathlib.Path,
        *,
        fail_cleanup: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        runtime.mkdir()
        env = os.environ.copy()
        if fail_cleanup:
            env["FAIL_CLEANUP"] = "1"
        return subprocess.run(
            ["sh", str(script), str(runtime), mode, str(image)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            env=env,
        )

    def start_signaled(
        self,
        script: pathlib.Path,
        runtime: pathlib.Path,
        mode: str,
        image: pathlib.Path,
        sig: signal.Signals,
        *,
        fail_cleanup: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        runtime.mkdir()
        env = os.environ.copy()
        if fail_cleanup:
            env["FAIL_CLEANUP"] = "1"
        process = subprocess.Popen(
            ["sh", str(script), str(runtime), mode, str(image)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=env,
        )
        deadline = time.monotonic() + 5
        ready = runtime / "ready"
        while time.monotonic() < deadline and not ready.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"harness exited before ready: {process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        self.assertTrue(ready.exists(), "harness did not become ready")
        os.kill(process.pid, sig)
        stdout, stderr = process.communicate(timeout=10)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    @staticmethod
    def private_dirs(image: pathlib.Path) -> list[pathlib.Path]:
        return list(image.parent.glob(f".{image.name}.mmdebstrap.*"))

    def assert_cleaned_once(self, runtime: pathlib.Path) -> None:
        self.assertEqual(
            (runtime / "cleanup.log").read_text(encoding="utf-8"), "cleanup\n"
        )
        self.assertFalse((runtime / "work").exists())

    def assert_cleaned_call_only(self, runtime: pathlib.Path) -> None:
        self.assertEqual(
            (runtime / "cleanup.log").read_text(encoding="utf-8"), "cleanup\n"
        )

    def test_ordinary_failure_preserves_existing_and_absent_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-failure-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            script = self.write_lifecycle_harness(root, candidate)

            existing = root / "existing.img"
            existing.write_bytes(b"sentinel\n")
            existing.chmod(0o600)
            result = self.run_harness(script, root / "run-existing", "failure", existing)
            self.assertEqual(result.returncode, 42, result.stdout + result.stderr)
            self.assertEqual(existing.read_bytes(), b"sentinel\n")
            self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o600)
            self.assertEqual(self.private_dirs(existing), [])
            self.assert_cleaned_once(root / "run-existing")

            absent = root / "absent.img"
            result = self.run_harness(script, root / "run-absent", "failure", absent)
            self.assertEqual(result.returncode, 42, result.stdout + result.stderr)
            self.assertFalse(absent.exists())
            self.assertEqual(self.private_dirs(absent), [])
            self.assert_cleaned_once(root / "run-absent")

    def test_wrapper_only_hup_int_term_and_immediate_rerun(self) -> None:
        cases = (
            (signal.SIGHUP, 129),
            (signal.SIGINT, 130),
            (signal.SIGTERM, 143),
        )
        with tempfile.TemporaryDirectory(prefix="qemu-composed-signals-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            script = self.write_lifecycle_harness(root, candidate)
            for sig, expected in cases:
                with self.subTest(signal=sig.name):
                    image = root / f"{sig.name.lower()}.img"
                    image.write_bytes(b"sentinel\n")
                    runtime = root / f"run-{sig.name.lower()}"
                    result = self.start_signaled(
                        script,
                        runtime,
                        "wait-before-publication",
                        image,
                        sig,
                    )
                    self.assertEqual(
                        result.returncode, expected, result.stdout + result.stderr
                    )
                    self.assertEqual(image.read_bytes(), b"sentinel\n")
                    self.assertFalse((runtime / "after").exists())
                    self.assertEqual(self.private_dirs(image), [])
                    self.assert_cleaned_once(runtime)

                    rerun = root / f"rerun-{sig.name.lower()}"
                    result = self.run_harness(script, rerun, "success", image)
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    self.assertEqual(image.read_bytes(), b"complete\n")
                    self.assertEqual(self.private_dirs(image), [])
                    self.assert_cleaned_once(rerun)

    def test_success_publishes_once_with_normal_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-success-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            script = self.write_lifecycle_harness(root, candidate)
            image = root / "image.img"
            image.write_bytes(b"sentinel\n")
            result = self.run_harness(script, root / "run", "success", image)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(image.read_bytes(), b"complete\n")
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o644)
            self.assertEqual(self.private_dirs(image), [])
            self.assert_cleaned_once(root / "run")

    def test_signal_after_publication_leaves_final_image(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-post-publish-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            script = self.write_lifecycle_harness(root, candidate)
            image = root / "image.img"
            image.write_bytes(b"sentinel\n")
            runtime = root / "run"
            result = self.start_signaled(
                script,
                runtime,
                "wait-after-publication",
                image,
                signal.SIGTERM,
            )
            self.assertEqual(result.returncode, 143, result.stdout + result.stderr)
            self.assertEqual(image.read_bytes(), b"complete\n")
            self.assertFalse((runtime / "after").exists())
            self.assertEqual(self.private_dirs(image), [])
            self.assert_cleaned_once(runtime)

    def test_cleanup_failure_precedence_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-cleanup-fail-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            script = self.write_lifecycle_harness(root, candidate)

            image = root / "success.img"
            result = self.run_harness(
                script,
                root / "success",
                "cleanup-only-success",
                image,
                fail_cleanup=True,
            )
            self.assertEqual(result.returncode, 74, result.stdout + result.stderr)
            self.assert_cleaned_call_only(root / "success")

            image = root / "failure.img"
            result = self.run_harness(
                script,
                root / "failure",
                "failure",
                image,
                fail_cleanup=True,
            )
            self.assertEqual(result.returncode, 42, result.stdout + result.stderr)
            self.assert_cleaned_call_only(root / "failure")

            image = root / "signal.img"
            runtime = root / "signal"
            result = self.start_signaled(
                script,
                runtime,
                "wait-before-publication",
                image,
                signal.SIGTERM,
                fail_cleanup=True,
            )
            self.assertEqual(result.returncode, 143, result.stdout + result.stderr)
            self.assert_cleaned_call_only(runtime)

    def test_root_and_symlink_to_root_are_rejected_before_mktemp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-root-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)
            prepare = self.extract_function(candidate, "prepare_image")
            script = root / "prepare-harness.sh"
            script.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "die() { echo \"$*\" >&2; exit 1; }\n"
                "IMAGE_TMPDIR=\n"
                "IMAGE_TMP=\n"
                "MKTEMP_LOG=$1\n"
                "IMAGE=$2\n"
                "mktemp() { printf 'called\\n' >\"$MKTEMP_LOG\"; return 99; }\n"
                + prepare
                + "\nprepare_image\n",
                encoding="utf-8",
            )
            checked = subprocess.run(["sh", "-n", str(script)])
            self.assertEqual(checked.returncode, 0)

            for label, image in (
                ("literal", pathlib.Path("/linux-fieldwork-qemu-test.img")),
                ("symlink", root / "root-link" / "linux-fieldwork-qemu-test.img"),
            ):
                if label == "symlink":
                    (root / "root-link").symlink_to("/", target_is_directory=True)
                log = root / f"{label}.log"
                completed = subprocess.run(
                    ["sh", str(script), str(log), str(image)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                self.assertEqual(completed.returncode, 1)
                self.assertIn("refusing to build an image directly below /", completed.stderr)
                self.assertFalse(log.exists())

    def test_complete_source_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qemu-composed-source-") as tmp:
            candidate = self.prepare_candidate(pathlib.Path(tmp))
            required = (
                'set -- "$@" -E "$EXTOPTS" "$IMAGE_TMP" "$SIZE"',
                'truncate --size="+$((34 * 512))" "$IMAGE_TMP"',
                '/sbin/sfdisk "$IMAGE_TMP" <<EOF',
                'dd if="$WORKDIR/fat" of="$IMAGE_TMP"',
                "trap exit_cleanup EXIT",
                "trap 'signal_exit 129' HUP",
                "trap 'signal_exit 130' INT",
                "trap 'signal_exit 131' QUIT",
                "trap 'signal_exit 143' TERM",
                "trap - EXIT HUP INT QUIT TERM",
            )
            for item in required:
                self.assertIn(item, candidate)
            self.assertEqual(
                candidate.count('mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"'),
                1,
            )
            self.assertLess(
                candidate.index("prepare_image\n", candidate.index("WORKDIR=$(mktemp -d)")),
                candidate.index("mmdebstrap \"$@\" |"),
            )
            self.assertLess(
                candidate.index("publish_image\n", candidate.index("dd if=")),
                candidate.index('echo "I: SUCCESS!'),
            )
            self.assertNotRegex(
                candidate,
                re.compile(r'^(?:truncate|/sbin/sfdisk|dd .* of=).*"\$IMAGE"', re.M),
            )


if __name__ == "__main__":
    unittest.main()
