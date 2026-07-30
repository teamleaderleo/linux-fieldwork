from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import socket
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/debian/tests/testsuite"
PATCH = (
    ROOT
    / "investigations/mmdebstrap-http-server-readiness"
    / "0001-verify-local-http-server.patch"
)


class MmdebstrapHttpServerReadinessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="mmdebstrap-http-ready-")
        self.addCleanup(self.tempdir.cleanup)
        self.work = pathlib.Path(self.tempdir.name)
        self.tree = self.work / "tree"
        destination = self.tree / "upstream/mmdebstrap/debian/tests"
        destination.mkdir(parents=True)
        self.candidate_source = destination / "testsuite"
        shutil.copy2(SOURCE, self.candidate_source)

        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=self.tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

        candidate = self.candidate_source.read_text(encoding="utf-8")
        begin = candidate.index("# BEGIN local mirror HTTP server helpers")
        end_marker = "# END local mirror HTTP server helpers"
        end = candidate.index(end_marker, begin) + len(end_marker)
        self.helpers = self.work / "http-server-helpers.sh"
        self.helpers.write_text(candidate[begin:end] + "\n", encoding="utf-8")

        self.server = self.work / "tcp-server.py"
        self.server.write_text(
            textwrap.dedent(
                """\
                import socket
                import sys
                import time

                port = int(sys.argv[1])
                delay = float(sys.argv[2])
                time.sleep(delay)
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", port))
                listener.listen()
                while True:
                    connection, _ = listener.accept()
                    connection.close()
                """
            ),
            encoding="utf-8",
        )

    def test_candidate_source_contract_and_syntax(self) -> None:
        baseline = SOURCE.read_text(encoding="utf-8")
        candidate = self.candidate_source.read_text(encoding="utf-8")

        self.assertIn("80 2>/dev/null &", baseline)
        self.assertIn('trap "kill $HTTPD_PID" INT QUIT TERM EXIT', baseline)
        self.assertNotIn("wait_for_http_server()", baseline)

        self.assertNotIn("80 2>/dev/null &", candidate)
        self.assertIn('HTTPD_LOG="$AUTOPKGTEST_TMP/http.server.log"', candidate)
        self.assertIn("wait_for_http_server()", candidate)
        self.assertIn("stop_http_server()", candidate)
        self.assertIn("probe_http_server()", candidate)
        self.assertIn("wait_for_http_server \"$HTTPD_PID\"", candidate)
        self.assertIn("trap 'stop_http_server \"$HTTPD_PID\"' EXIT", candidate)
        self.assertNotIn('trap "kill $HTTPD_PID"', candidate)

        syntax = subprocess.run(
            ["sh", "-n", str(self.candidate_source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)

    def test_delayed_start_becomes_ready_and_is_reaped(self) -> None:
        port = self.free_port()
        completed = self.run_shell(
            """
            python3 "$SERVER" "$PORT" 0.2 2>"$LOG" &
            pid=$!
            trap 'stop_http_server "$pid"' EXIT
            wait_for_http_server "$pid" "$LOG" 127.0.0.1 "$PORT" 20
            stop_http_server "$pid"
            trap - EXIT
            if kill -0 "$pid" 2>/dev/null; then
                echo "server survived cleanup" >&2
                exit 1
            fi
            """,
            port,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_immediate_exit_is_classified_and_stderr_is_retained(self) -> None:
        port = self.free_port()
        completed = self.run_shell(
            """
            sh -c 'echo immediate-startup-failure >&2; exit 23' 2>"$LOG" &
            pid=$!
            trap 'stop_http_server "$pid"' EXIT
            if wait_for_http_server "$pid" "$LOG" 127.0.0.1 "$PORT" 5; then
                echo "dead server reported ready" >&2
                exit 1
            fi
            stop_http_server "$pid"
            trap - EXIT
            """,
            port,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(
            "local mirror HTTP server exited before becoming ready",
            completed.stderr,
        )
        self.assertIn("immediate-startup-failure", completed.stderr)

    def test_occupied_port_reports_the_bind_failure(self) -> None:
        port = self.free_port()
        completed = self.run_shell(
            """
            python3 "$SERVER" "$PORT" 0 2>"$WORK/holder.log" &
            holder=$!
            trap 'stop_http_server "$holder"' EXIT
            wait_for_http_server "$holder" "$WORK/holder.log" 127.0.0.1 "$PORT" 20

            python3 "$SERVER" "$PORT" 0 2>"$LOG" &
            candidate=$!
            trap 'stop_http_server "$candidate"; stop_http_server "$holder"' EXIT
            if wait_for_http_server "$candidate" "$LOG" 127.0.0.1 "$PORT" 10; then
                echo "second server incorrectly reported ready" >&2
                exit 1
            fi
            stop_http_server "$candidate"
            stop_http_server "$holder"
            trap - EXIT
            """,
            port,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(
            "local mirror HTTP server exited before becoming ready",
            completed.stderr,
        )
        self.assertIn("Address already in use", completed.stderr)

    def test_timeout_and_cleanup_of_already_exited_process(self) -> None:
        port = self.free_port()
        completed = self.run_shell(
            """
            sleep 30 &
            sleeper=$!
            trap 'stop_http_server "$sleeper"' EXIT
            if wait_for_http_server "$sleeper" "$LOG" 127.0.0.1 "$PORT" 3; then
                echo "non-listening process incorrectly reported ready" >&2
                exit 1
            fi
            stop_http_server "$sleeper"
            trap - EXIT
            if kill -0 "$sleeper" 2>/dev/null; then
                echo "timeout process survived cleanup" >&2
                exit 1
            fi

            sh -c 'exit 0' &
            exited=$!
            wait "$exited"
            stop_http_server "$exited"
            """,
            port,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn(
            "local mirror HTTP server did not become ready",
            completed.stderr,
        )

    def run_shell(self, body: str, port: int) -> subprocess.CompletedProcess[str]:
        script = self.work / "scenario.sh"
        script.write_text(
            "set -eu\n"
            + f". {shlex.quote(str(self.helpers))}\n"
            + textwrap.dedent(body),
            encoding="utf-8",
        )
        log = self.work / "server.log"
        log.write_text("", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "SERVER": str(self.server),
                "PORT": str(port),
                "LOG": str(log),
                "WORK": str(self.work),
            }
        )
        return subprocess.run(
            ["sh", str(script)],
            cwd=self.work,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

    @staticmethod
    def free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return int(listener.getsockname()[1])


if __name__ == "__main__":
    unittest.main()
