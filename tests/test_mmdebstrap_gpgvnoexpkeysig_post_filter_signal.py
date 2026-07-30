from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import tempfile
import time
import unittest


class GpgvNoExpKeySigPostFilterSignalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/gpgvnoexpkeysig"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-gpgvnoexpkeysig-canonical/"
            "0001-canonical-lifecycle.patch"
        )

    def prepare_candidate(self, root: pathlib.Path) -> str:
        tree = root / "candidate"
        destination = tree / "upstream/mmdebstrap/gpgvnoexpkeysig"
        destination.parent.mkdir(parents=True)
        destination.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        destination.chmod(0o755)
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

    def predecessor(self, candidate: str) -> str:
        predecessor = candidate
        replacements = (
            ("FILTER_STARTED=no\n", ""),
            (
                "  signal_number=$2\n  trap - EXIT\n",
                "  signal_number=$2\n  filter_was_running=no\n  trap - EXIT\n",
            ),
            (
                '  if [ -n "$FILTER_PID" ] && kill -0 "$FILTER_PID" 2>/dev/null; then\n'
                '    kill -"$signal_number" "$FILTER_PID" 2>/dev/null || :\n',
                '  if [ -n "$FILTER_PID" ] && kill -0 "$FILTER_PID" 2>/dev/null; then\n'
                '    filter_was_running=yes\n'
                '    kill -"$signal_number" "$FILTER_PID" 2>/dev/null || :\n',
            ),
            (
                '  if [ "$FILTER_STARTED" = no ] && [ -s "$STATUS_FILE" ]; then\n',
                '  if [ "$filter_was_running" = no ] && [ -s "$STATUS_FILE" ]; then\n',
            ),
            ("  FILTER_STARTED=yes\n", ""),
        )
        for old, new in replacements:
            self.assertEqual(predecessor.count(old), 1, old)
            predecessor = predecessor.replace(old, new, 1)
        return predecessor

    @staticmethod
    def write_executable(path: pathlib.Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def write_fake_commands(self, root: pathlib.Path) -> pathlib.Path:
        fake_bin = root / "bin"
        fake_bin.mkdir()
        self.write_executable(
            fake_bin / "gpgv",
            "#!/bin/sh\n"
            "printf '[GNUPG:] EXPKEYSIG KEY User\\n'\n",
        )
        self.write_executable(
            fake_bin / "sed",
            "#!/bin/sh\n"
            "printf 'sed\\n' >>\"$SED_LOG\"\n"
            "exec /bin/sed \"$@\"\n",
        )
        self.write_executable(
            fake_bin / "rm",
            "#!/bin/sh\n"
            "count=0\n"
            "if test -f \"$RM_COUNT\"; then read -r count <\"$RM_COUNT\"; fi\n"
            "count=$((count + 1))\n"
            "printf '%s\\n' \"$count\" >\"$RM_COUNT\"\n"
            "if test \"$count\" -eq 1; then\n"
            "  : >\"$RM_READY\"\n"
            "  while ! test -e \"$RM_RELEASE\"; do sleep 0.01; done\n"
            "  exit 0\n"
            "fi\n"
            "exec /bin/rm \"$@\"\n",
        )
        return fake_bin

    def run_case(
        self, root: pathlib.Path, source: str
    ) -> subprocess.CompletedProcess[str]:
        wrapper = root / "gpgvnoexpkeysig"
        self.write_executable(wrapper, source)
        fake_bin = self.write_fake_commands(root)
        tmpdir = root / "tmp"
        tmpdir.mkdir()
        ready = root / "rm-ready"
        release = root / "rm-release"
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "TMPDIR": str(tmpdir),
                "SED_LOG": str(root / "sed.log"),
                "RM_COUNT": str(root / "rm.count"),
                "RM_READY": str(ready),
                "RM_RELEASE": str(release),
            }
        )
        process = subprocess.Popen(
            ["sh", str(wrapper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not ready.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    f"wrapper exited before cleanup window: "
                    f"{process.returncode}: {stdout}{stderr}"
                )
            time.sleep(0.01)
        self.assertTrue(ready.exists(), "cleanup window did not open")
        os.kill(process.pid, signal.SIGTERM)
        release.touch()
        stdout, stderr = process.communicate(timeout=10)
        return subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

    def test_signal_after_filter_completion_does_not_replay_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="gpgv-post-filter-signal-") as tmp:
            root = pathlib.Path(tmp)
            candidate = self.prepare_candidate(root)

            predecessor_root = root / "predecessor"
            predecessor_root.mkdir()
            predecessor = self.run_case(predecessor_root, self.predecessor(candidate))
            self.assertEqual(predecessor.returncode, 143, predecessor.stderr)
            self.assertEqual(
                predecessor.stdout,
                "[GNUPG:] GOODSIG KEY User\n[GNUPG:] GOODSIG KEY User\n",
            )
            self.assertEqual(
                (predecessor_root / "sed.log").read_text(encoding="utf-8"),
                "sed\nsed\n",
            )

            candidate_root = root / "repaired"
            candidate_root.mkdir()
            repaired = self.run_case(candidate_root, candidate)
            self.assertEqual(repaired.returncode, 143, repaired.stderr)
            self.assertEqual(repaired.stdout, "[GNUPG:] GOODSIG KEY User\n")
            self.assertEqual(
                (candidate_root / "sed.log").read_text(encoding="utf-8"),
                "sed\n",
            )
            self.assertEqual(list((candidate_root / "tmp").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
