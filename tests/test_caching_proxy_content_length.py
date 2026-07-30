from __future__ import annotations

import http.client
import http.server
import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
ATOMIC_PATCH = (
    ROOT
    / "investigations/caching-proxy-atomic-publication"
    / "0001-publish-cache-files-atomically.patch"
)
LENGTH_PATCH = (
    ROOT
    / "investigations/caching-proxy-content-length"
    / "0001-reject-short-upstream-responses.patch"
)
FIRST_CHUNK = b"A" * (64 * 1024)
SECOND_CHUNK = b"B" * (64 * 1024)
FULL_BODY = FIRST_CHUNK + SECOND_CHUNK
NO_LENGTH_BODY = b"NO-CONTENT-LENGTH"


class RecoveringUpstream(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.endswith("/nolength"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(NO_LENGTH_BODY)
            self.wfile.flush()
            self.close_connection = True
            return

        with self.server.request_lock:
            self.server.request_count += 1
            request_number = self.server.request_count
        self.send_response(200)
        self.send_header("Content-Length", str(len(FULL_BODY)))
        self.end_headers()
        if request_number == 1:
            self.wfile.write(FIRST_CHUNK)
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(FULL_BODY)
        self.wfile.flush()

    def log_message(self, _format: str, *args: object) -> None:
        return


class CachingProxyContentLengthTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="caching-proxy-length-")
        self.addCleanup(self.tempdir.cleanup)
        self.work = pathlib.Path(self.tempdir.name)

        self.atomic_tree = self.work / "atomic-tree"
        atomic_dir = self.atomic_tree / "upstream/mmdebstrap"
        atomic_dir.mkdir(parents=True)
        self.atomic_source = atomic_dir / "caching_proxy.py"
        shutil.copy2(SOURCE, self.atomic_source)
        self.apply_patch(self.atomic_tree, ATOMIC_PATCH)

        self.candidate_tree = self.work / "candidate-tree"
        candidate_dir = self.candidate_tree / "upstream/mmdebstrap"
        candidate_dir.mkdir(parents=True)
        self.candidate_source = candidate_dir / "caching_proxy.py"
        shutil.copy2(self.atomic_source, self.candidate_source)
        self.apply_patch(self.candidate_tree, LENGTH_PATCH)

    def test_atomic_only_source_publishes_a_short_upstream_response(self) -> None:
        module = self.load_module(self.atomic_source)
        oldcache = self.work / "baseline-old"
        newcache = self.work / "baseline-new"
        oldcache.mkdir()
        newcache.mkdir()
        final_path = newcache / "pool/pkg.deb"

        with self.upstream_server() as upstream, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port:
            first = self.proxy_get(proxy_port, upstream.port, "pool/pkg.deb")
            self.assertTrue(first.incomplete)
            self.assertEqual(first.status, 200)
            self.assertEqual(first.content_length, len(FULL_BODY))
            self.assertEqual(first.body, FIRST_CHUNK)
            self.wait_for_bytes(final_path, FIRST_CHUNK)

            second = self.proxy_get(proxy_port, upstream.port, "pool/pkg.deb")

        self.assertFalse(second.incomplete)
        self.assertEqual(second.status, 200)
        self.assertEqual(second.content_length, len(FIRST_CHUNK))
        self.assertEqual(second.body, FIRST_CHUNK)
        self.assertEqual(upstream.request_count, 1)
        self.assertEqual(final_path.read_bytes(), FIRST_CHUNK)

    def test_candidate_discards_short_fill_and_recovers_on_next_request(self) -> None:
        module = self.load_module(self.candidate_source)
        oldcache = self.work / "candidate-old"
        newcache = self.work / "candidate-new"
        oldcache.mkdir()
        newcache.mkdir()
        final_path = newcache / "pool/pkg.deb"

        with self.upstream_server() as upstream, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port:
            first = self.proxy_get(proxy_port, upstream.port, "pool/pkg.deb")
            self.assertTrue(first.incomplete)
            self.assertEqual(first.status, 200)
            self.assertEqual(first.content_length, len(FULL_BODY))
            self.assertTrue(first.body.startswith(FIRST_CHUNK))
            self.wait_for_absence(final_path)
            self.assertEqual(list((newcache / "pool").glob(".pkg.deb.*")), [])

            second = self.proxy_get(proxy_port, upstream.port, "pool/pkg.deb")

        self.assertFalse(second.incomplete)
        self.assertEqual(second.status, 200)
        self.assertEqual(second.content_length, len(FULL_BODY))
        self.assertEqual(second.body, FULL_BODY)
        self.assertEqual(upstream.request_count, 2)
        self.assertEqual(final_path.read_bytes(), FULL_BODY)
        self.assertEqual(list(final_path.parent.glob(".pkg.deb.*")), [])

    def test_candidate_keeps_responses_without_content_length(self) -> None:
        module = self.load_module(self.candidate_source)
        oldcache = self.work / "nolength-old"
        newcache = self.work / "nolength-new"
        oldcache.mkdir()
        newcache.mkdir()
        final_path = newcache / "pool/nolength"

        with self.upstream_server() as upstream, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port:
            response = self.proxy_get(proxy_port, upstream.port, "pool/nolength")

        self.assertFalse(response.incomplete)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_length, -1)
        self.assertEqual(response.body, NO_LENGTH_BODY)
        self.assertEqual(final_path.read_bytes(), NO_LENGTH_BODY)

    def test_candidate_source_contract_and_compilation(self) -> None:
        atomic = self.atomic_source.read_text(encoding="utf-8")
        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertNotIn("expected_length =", atomic)
        self.assertIn('expected_length = res.getheader("Content-Length")', candidate)
        self.assertIn("received += len(buf)", candidate)
        self.assertIn("received != expected_length", candidate)
        self.assertIn("http.client.IncompleteRead", candidate)

        compiled = subprocess.run(
            ["python3", "-m", "py_compile", str(self.candidate_source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

    @staticmethod
    def apply_patch(tree: pathlib.Path, patch: pathlib.Path) -> None:
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            raise AssertionError(applied.stdout + applied.stderr)

    def load_module(self, path: pathlib.Path):
        name = f"caching_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def proxy_server(self, module, oldcache: pathlib.Path, newcache: pathlib.Path):
        module.oldcachedir = oldcache
        module.newcachedir = newcache
        module.readonly = False
        module.ProxyRequestHandler.log_message = lambda *_args: None
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), module.ProxyRequestHandler
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return RunningServer(server, thread)

    def upstream_server(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RecoveringUpstream)
        server.daemon_threads = True
        server.request_lock = threading.Lock()
        server.request_count = 0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return RunningUpstream(server, thread)

    @staticmethod
    def proxy_get(proxy_port: int, upstream_port: int, suffix: str):
        host = f"127.0.0.1:{upstream_port}"
        target = f"http://{host}/{suffix}"
        connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=10)
        connection.putrequest("GET", target, skip_host=True)
        connection.putheader("Host", host)
        connection.endheaders()
        response = connection.getresponse()
        content_length = int(response.getheader("Content-Length", "-1"))
        incomplete = False
        try:
            body = response.read()
        except http.client.IncompleteRead as error:
            body = error.partial
            incomplete = True
        status = response.status
        connection.close()
        return ProxyResponse(status, content_length, body, incomplete)

    @staticmethod
    def wait_for_bytes(path: pathlib.Path, expected: bytes) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists() and path.read_bytes() == expected:
                return
            time.sleep(0.01)
        actual = path.read_bytes() if path.exists() else None
        raise AssertionError(f"cache bytes mismatch: {actual!r}")

    @staticmethod
    def wait_for_absence(path: pathlib.Path) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not path.exists():
                return
            time.sleep(0.01)
        raise AssertionError(f"short cache file survived: {path.stat().st_size} bytes")


class ProxyResponse:
    def __init__(self, status: int, content_length: int, body: bytes, incomplete: bool):
        self.status = status
        self.content_length = content_length
        self.body = body
        self.incomplete = incomplete


class RunningServer:
    def __init__(self, server: http.server.ThreadingHTTPServer, thread: threading.Thread):
        self.server = server
        self.thread = thread

    def __enter__(self) -> int:
        return int(self.server.server_address[1])

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise AssertionError("server thread survived shutdown")


class RunningUpstream(RunningServer):
    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    @property
    def request_count(self) -> int:
        with self.server.request_lock:
            return int(self.server.request_count)

    def __enter__(self):
        return self


if __name__ == "__main__":
    unittest.main()
