from __future__ import annotations

import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = ROOT / (
    "investigations/mmdebstrap-caching-proxy-containment/"
    "0001-confine-cache-paths.patch"
)

LAUNCHER = r'''
import importlib.util
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
old_cache = pathlib.Path(sys.argv[2])
new_cache = pathlib.Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("optimized_proxy", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.oldcachedir = old_cache
module.newcachedir = new_cache
module.readonly = False

class QuietHandler(module.ProxyRequestHandler):
    def log_message(self, _format, *args):
        return None

server = module.http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
server.daemon_threads = True
print(server.server_address[1], flush=True)
server.serve_forever()
'''


class MmdebstrapCachingProxyOptimizedValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="caching-proxy-optimized-validation-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)
        self.launcher = self.work / "launcher.py"
        self.launcher.write_text(textwrap.dedent(LAUNCHER), encoding="utf-8")

    def prepare_source(self, *, patched: bool) -> pathlib.Path:
        tree = self.work / ("candidate" if patched else "baseline")
        destination = tree / "upstream/mmdebstrap/caching_proxy.py"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        if patched:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
                cwd=tree,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        return destination

    def start_proxy(self, source: pathlib.Path) -> tuple[subprocess.Popen[str], int]:
        old_cache = self.work / f"{source.parent.parent.parent.name}-old"
        new_cache = self.work / f"{source.parent.parent.parent.name}-new"
        old_cache.mkdir(exist_ok=True)
        new_cache.mkdir(exist_ok=True)
        process = subprocess.Popen(
            [
                sys.executable,
                "-O",
                str(self.launcher),
                str(source),
                str(old_cache),
                str(new_cache),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop_proxy, process)
        assert process.stdout is not None
        line = process.stdout.readline().strip()
        if not line:
            assert process.stderr is not None
            stderr = process.stderr.read()
            process.wait(timeout=5)
            self.fail(f"optimized proxy did not report a port: {stderr}")
        return process, int(line)

    @staticmethod
    def stop_proxy(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    @staticmethod
    def raw_request(port: int, target: str, content_length: str = "0") -> bytes:
        request = (
            f"GET {target} HTTP/1.1\r\n"
            "Host: proxy.invalid\r\n"
            f"Content-Length: {content_length}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.settimeout(5)
            client.sendall(request)
            response = bytearray()
            while True:
                block = client.recv(4096)
                if not block:
                    break
                response.extend(block)
        return bytes(response)

    @staticmethod
    def status(response: bytes) -> int:
        line = response.split(b"\r\n", 1)[0]
        return int(line.split(b" ", 2)[1])

    def test_imported_source_under_optimization_serves_absolute_host_file(self) -> None:
        outside = self.work / "outside-host-file.deb"
        payload = b"optimized-assert-bypass\n"
        outside.write_bytes(payload)
        _process, port = self.start_proxy(self.prepare_source(patched=False))

        response = self.raw_request(port, str(outside), content_length="1")

        self.assertEqual(self.status(response), 200)
        self.assertEqual(response.split(b"\r\n\r\n", 1)[1], payload)

    def test_candidate_under_optimization_rejects_before_host_file_access(self) -> None:
        outside = self.work / "outside-candidate.deb"
        payload = b"must-not-be-served\n"
        outside.write_bytes(payload)
        _process, port = self.start_proxy(self.prepare_source(patched=True))

        response = self.raw_request(port, str(outside), content_length="1")

        self.assertEqual(self.status(response), 400)
        self.assertNotIn(payload, response)
        self.assertEqual(outside.read_bytes(), payload)

    def test_candidate_ordinary_and_optimized_source_compile(self) -> None:
        candidate = self.prepare_source(patched=True)
        for optimize in ([], ["-O"]):
            completed = subprocess.run(
                [sys.executable, *optimize, "-m", "py_compile", str(candidate)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )


if __name__ == "__main__":
    unittest.main()
