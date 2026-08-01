from __future__ import annotations

import os
import pathlib
import signal
import stat
import subprocess
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch"
DEFAULT_REPO = pathlib.Path(__file__).resolve().parents[4] if len(pathlib.Path(__file__).resolve().parents) > 4 else pathlib.Path("/")
SOURCE = pathlib.Path(os.environ.get("MMDEBSTRAP_QEMU_SOURCE", DEFAULT_REPO / "upstream/mmdebstrap/mmdebstrap-autopkgtest-build-qemu"))


def added_candidate_shell() -> str:
    lines = []
    for line in PATCH.read_text(encoding="utf-8").splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def extract_function(source: str, name: str) -> str:
    marker = f"{name}() {{\n"
    start = source.index(marker) if source.startswith(marker) else source.index("\n" + marker) + 1
    end = source.index("\n}\n", start) + 3
    return source[start:end]


class PacketPatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.patch = PATCH.read_text(encoding="utf-8")
        cls.added = added_candidate_shell()
        cleanup_start = cls.added.index("  cleanup_status=0\n")
        cleanup_end = cls.added.index('  return "$cleanup_status"\n', cleanup_start) + len('  return "$cleanup_status"\n')
        cleanup = "cleanup() {\n" + cls.added[cleanup_start:cleanup_end] + "}\n"
        cls.functions = "\n".join(
            [extract_function(cls.added, "prepare_image"), extract_function(cls.added, "publish_image"), cleanup, extract_function(cls.added, "exit_cleanup"), extract_function(cls.added, "signal_exit")]
        )
        traps = [
            line for line in cls.added.splitlines()
            if line.startswith("trap exit_cleanup") or line.startswith("trap 'signal_exit")
        ]
        cls.traps = "\n".join(traps) + "\n"

    def write_harness(self, root: pathlib.Path) -> pathlib.Path:
        functions = self.functions.replace("cleanup() {", "product_cleanup() {", 1)
        script = root / "harness.sh"
        script.write_text(
            "#!/bin/sh\nset -eu\n"
            "die() { echo \"$*\" >&2; exit 1; }\n"
            "WORKDIR=\nIMAGE_TMPDIR=\nIMAGE_TMP=\nIN_CLEANUP=0\n"
            "FAIL_CLEANUP=${FAIL_CLEANUP:-0}\n"
            "rm() { if test \"$IN_CLEANUP\" -eq 1 && test \"$FAIL_CLEANUP\" -eq 1; then return 73; fi; command rm \"$@\"; }\n"
            "rmdir() { if test \"$IN_CLEANUP\" -eq 1 && test \"$FAIL_CLEANUP\" -eq 1; then return 74; fi; command rmdir \"$@\"; }\n"
            + functions
            + "\ncleanup() { printf 'cleanup\\n' >>\"$CLEANUP_LOG\"; IN_CLEANUP=1; result=0; product_cleanup || result=$?; IN_CLEANUP=0; return \"$result\"; }\n"
            + self.traps
            + "RUNTIME=$1\nMODE=$2\nIMAGE=$3\nCLEANUP_LOG=$RUNTIME/cleanup.log\n"
            "WORKDIR=$RUNTIME/work\nmkdir \"$WORKDIR\"\nprintf owned >\"$WORKDIR/owned\"\n"
            "prepare_image\numask 022\nprintf partial >\"$IMAGE_TMP\"\n"
            "case $MODE in\n"
            " failure) exit 42 ;;\n"
            " wait-before) printf ready >\"$RUNTIME/ready\"; sleep 0.25; printf complete >\"$IMAGE_TMP\"; publish_image ;;\n"
            " success) printf complete >\"$IMAGE_TMP\"; publish_image ;;\n"
            " wait-after) printf complete >\"$IMAGE_TMP\"; publish_image; printf ready >\"$RUNTIME/ready\"; sleep 0.25 ;;\n"
            " cleanup-only) : ;;\n"
            "esac\nprintf after >\"$RUNTIME/after\"\n",
            encoding="utf-8",
        )
        checked = subprocess.run(["sh", "-n", str(script)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        return script

    @staticmethod
    def run_harness(script: pathlib.Path, runtime: pathlib.Path, mode: str, image: pathlib.Path, fail_cleanup: bool = False):
        runtime.mkdir()
        env = os.environ.copy()
        if fail_cleanup:
            env["FAIL_CLEANUP"] = "1"
        return subprocess.run(["sh", str(script), str(runtime), mode, str(image)], capture_output=True, text=True, env=env, timeout=10)

    @staticmethod
    def signal_run(script: pathlib.Path, runtime: pathlib.Path, mode: str, image: pathlib.Path, sig: signal.Signals):
        runtime.mkdir()
        proc = subprocess.Popen(["sh", str(script), str(runtime), mode, str(image)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (runtime / "ready").exists():
            if proc.poll() is not None:
                out, err = proc.communicate()
                raise AssertionError(f"early exit {proc.returncode}: {out}{err}")
            time.sleep(0.01)
        os.kill(proc.pid, sig)
        out, err = proc.communicate(timeout=10)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    @staticmethod
    def private_dirs(image: pathlib.Path):
        return list(image.parent.glob(f".{image.name}.mmdebstrap.*"))

    def test_upstream_paths_coordinates_and_single_publication(self):
        self.assertIn("diff --git a/mmdebstrap-autopkgtest-build-qemu b/mmdebstrap-autopkgtest-build-qemu", self.patch)
        self.assertNotIn("upstream/mmdebstrap/", self.patch)
        self.assertNotIn("@@ -1,12 +1,78 @@", self.patch)
        self.assertIn("@@ -318,12 +318,78 @@", self.patch)
        self.assertIn("@@ -406,7 +472,7 @@", self.patch)
        self.assertIn("@@ -465,8 +531,8 @@", self.patch)
        self.assertIn("@@ -474,7 +540,7 @@", self.patch)
        self.assertIn("@@ -483,5 +549,7 @@", self.patch)
        self.assertEqual(self.patch.count('mv --no-target-directory -- "$IMAGE_TMP" "$IMAGE"'), 1)
        self.assertIn('set -- "$@" -E "$EXTOPTS" "$IMAGE_TMP" "$SIZE"', self.patch)
        self.assertIn('/sbin/sfdisk "$IMAGE_TMP" <<EOF', self.patch)
        self.assertIn('dd if="$WORKDIR/fat" of="$IMAGE_TMP"', self.patch)

    def test_patch_applies_without_offset_or_fuzz_to_exact_imported_source(self):
        if not SOURCE.exists():
            self.skipTest(f"exact imported source unavailable at {SOURCE}")
        with tempfile.TemporaryDirectory(prefix="unit04-apply-") as td:
            root = pathlib.Path(td)
            candidate = root / "mmdebstrap-autopkgtest-build-qemu"
            candidate.write_bytes(SOURCE.read_bytes())
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i", str(PATCH)],
                cwd=root, capture_output=True, text=True
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
            transcript = applied.stdout + applied.stderr
            self.assertNotIn("offset", transcript.lower())
            self.assertNotIn("fuzz", transcript.lower())
            checked = subprocess.run(["sh", "-n", str(candidate)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_failure_preserves_existing_and_absent(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); script = self.write_harness(root)
            image = root / "existing.img"; image.write_bytes(b"sentinel"); image.chmod(0o600)
            r = self.run_harness(script, root / "run1", "failure", image)
            self.assertEqual(r.returncode, 42); self.assertEqual(image.read_bytes(), b"sentinel")
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o600); self.assertEqual(self.private_dirs(image), [])
            absent = root / "absent.img"; r = self.run_harness(script, root / "run2", "failure", absent)
            self.assertEqual(r.returncode, 42); self.assertFalse(absent.exists()); self.assertEqual(self.private_dirs(absent), [])

    def test_hup_int_term_and_rerun(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); script = self.write_harness(root)
            for sig, code in ((signal.SIGHUP, 129), (signal.SIGINT, 130), (signal.SIGTERM, 143)):
                image = root / f"{sig.name}.img"; image.write_bytes(b"sentinel")
                runtime = root / f"run-{sig.name}"
                r = self.signal_run(script, runtime, "wait-before", image, sig)
                self.assertEqual(r.returncode, code); self.assertEqual(image.read_bytes(), b"sentinel")
                self.assertFalse((runtime / "after").exists()); self.assertEqual(self.private_dirs(image), [])
                rerun = root / f"rerun-{sig.name}"; r = self.run_harness(script, rerun, "success", image)
                self.assertEqual(r.returncode, 0); self.assertEqual(image.read_bytes(), b"complete")

    def test_success_mode_and_post_publication_term(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); script = self.write_harness(root)
            image = root / "success.img"; image.write_bytes(b"sentinel")
            r = self.run_harness(script, root / "success", "success", image)
            self.assertEqual(r.returncode, 0); self.assertEqual(image.read_bytes(), b"complete")
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o644)
            image2 = root / "after.img"; image2.write_bytes(b"sentinel")
            r = self.signal_run(script, root / "after", "wait-after", image2, signal.SIGTERM)
            self.assertEqual(r.returncode, 143); self.assertEqual(image2.read_bytes(), b"complete")

    def test_cleanup_precedence(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); script = self.write_harness(root)
            r = self.run_harness(script, root / "success", "cleanup-only", root / "a.img", True)
            self.assertEqual(r.returncode, 74)
            r = self.run_harness(script, root / "failure", "failure", root / "b.img", True)
            self.assertEqual(r.returncode, 42)

    def test_trailing_slash_rejected_before_mktemp(self):
        prepare = extract_function(self.added, "prepare_image")
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td); dest = root / "existing"; dest.mkdir(); log = root / "mktemp.log"
            script = root / "prepare.sh"
            script.write_text("#!/bin/sh\nset -eu\ndie() { echo \"$*\" >&2; exit 1; }\nIMAGE_TMPDIR=\nIMAGE_TMP=\nMKTEMP_LOG=$1\nIMAGE=$2\nmktemp() { echo called >\"$MKTEMP_LOG\"; return 99; }\n" + prepare + "\nprepare_image\n", encoding="utf-8")
            r = subprocess.run(["sh", str(script), str(log), f"{dest}/"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn("invalid image path", r.stderr); self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
