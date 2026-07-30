from __future__ import annotations

import concurrent.futures
import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import shutil
import socket
import stat
import subprocess
import tempfile
import threading
import time
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = ROOT / (
    "investigations/caching-proxy-core-stack/"
    "0001-compose-atomic-framing-length.patch"
)
HALF = b"A" * (64 * 1024)
COMPLETE = HALF + (b"B" * (64 * 1024))
CHUNKED = b"decoded-chunked-payload\n"
NO_LENGTH = b"eof-framed-payload\n"
NEGATIVE_LENGTH = b"negative-length-payload\n"


class StackOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        with self.server.lock:
            self.server.counts[self.path] = self.server.counts.get(self.path, 0) + 1
            count = self.server.counts[self.path]

        if self.path == "http://127.0.0.1:%d/atomic" % self.server.server_address[1]:
            self.send_response(200)
            self.send_header("Content-Length", str(len(COMPLETE)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(HALF)
            self.wfile.flush()
            self.server.atomic_started.set()
            if self.server.atomic_release.wait(timeout=10):
                self.wfile.write(COMPLETE[len(HALF) :])
                self.wfile.flush()
            return

        if self.path.endswith("/recover"):
            self.send_response(200)
            self.send_header("Content-Length", str(len(COMPLETE)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(HALF if count == 1 else COMPLETE)
            self.wfile.flush()
            return

        if self.path.endswith("/chunked"):
            self.send_response_only(200, "OK")
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Content-Length", "999")
            self.send_header("Connection", "close, X-Hop")
            self.send_header("Keep-Alive", "timeout=5")
            self.send_header("X-Hop", "remove-me")
            self.send_header("X-End-To-End", "retained")
            self.end_headers()
            pieces = (CHUNKED[:8], CHUNKED[8:])
            for piece in pieces:
                self.wfile.write(f"{len(piece):X}\r\n".encode("ascii"))
                self.wfile.write(piece + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
            return

        if self.path.endswith("/nolength"):
            self.send_response(200)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(NO_LENGTH)
            self.wfile.flush()
            return

        if self.path.endswith("/negative"):
            self.send_response_only(200, "OK")
            self.send_header("Content-Length", "-1")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(NEGATIVE_LENGTH)
            self.wfile.flush()
            return

        self.send_error(404)

    def log_message(self, _format: str, *args: object) -> None:
        return


@contextlib.contextmanager
def running_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.lock = threading.Lock()
    server.counts = {}
    server.atomic_started = threading.Event()
    server.atomic_release = threading.Event()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.atomic_release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("HTTP server thread survived shutdown")


class CachingProxyCoreStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="caching-proxy-core-stack-")
        cls.work = pathlib.Path(cls.temporary.name)
        cls.tree = cls.work / "candidate"
        destination = cls.tree / "upstream/mmdebstrap/caching_proxy.py"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=cls.tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if applied.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        compiled = subprocess.run(
            ["python3", "-m", "py_compile", str(destination)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if compiled.returncode != 0:
            cls.temporary.cleanup()
            raise AssertionError(compiled.stdout + compiled.stderr)
        cls.source = destination

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def setUp(self) -> None:
        self.case = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.work))
        self.addCleanup(shutil.rmtree, self.case)

    def load_module(self):
        name = f"caching_proxy_stack_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, self.source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def running_proxy(self):
        module = self.load_module()
        old_cache = self.case / "old"
        new_cache = self.case / "new"
        old_cache.mkdir()
        new_cache.mkdir()
        module.oldcachedir = old_cache
        module.newcachedir = new_cache
        module.readonly = False

        class QuietHandler(module.ProxyRequestHandler):
            def log_message(self, _format: str, *args: object) -> None:
                return

        with running_server(QuietHandler) as server:
            yield server, new_cache

    @staticmethod
    def proxy_get(proxy_port: int, origin_port: int, path: str) -> tuple[int, bytes]:
        host = f"127.0.0.1:{origin_port}"
        target = f"http://{host}/{path}"
        connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=10)
        connection.putrequest("GET", target, skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", host)
        connection.putheader("Connection", "close")
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        status = response.status
        connection.close()
        return status, body

    @staticmethod
    def raw_get(proxy_port: int, origin_port: int, path: str) -> bytes:
        host = f"127.0.0.1:{origin_port}"
        target = f"http://{host}/{path}"
        request = (
            f"GET {target} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=5) as client:
            client.settimeout(10)
            client.sendall(request)
            result = bytearray()
            while True:
                block = client.recv(65536)
                if not block:
                    break
                result.extend(block)
        return bytes(result)

    @staticmethod
    def wait_for_count(origin, path: str, expected: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with origin.lock:
                count = origin.counts.get(path, 0)
            if count >= expected:
                return
            time.sleep(0.01)
        raise AssertionError(f"origin count for {path} did not reach {expected}")

    def test_atomic_publication_preserves_mode_and_complete_clients(self) -> None:
        with running_server(StackOrigin) as origin, self.running_proxy() as (
            proxy,
            cache,
        ), concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            origin_port = int(origin.server_address[1])
            proxy_port = int(proxy.server_address[1])
            reference = cache / "mode-reference"
            with reference.open("wb"):
                pass
            expected_mode = stat.S_IMODE(reference.stat().st_mode)
            reference.unlink()

            first = executor.submit(self.proxy_get, proxy_port, origin_port, "atomic")
            self.assertTrue(origin.atomic_started.wait(timeout=5))
            final = cache / "atomic"
            self.assertFalse(final.exists())
            second = executor.submit(self.proxy_get, proxy_port, origin_port, "atomic")
            self.wait_for_count(origin, f"http://127.0.0.1:{origin_port}/atomic", 2)
            self.assertFalse(final.exists())
            origin.atomic_release.set()
            results = (first.result(timeout=10), second.result(timeout=10))

        for status, body in results:
            self.assertEqual(status, 200)
            self.assertEqual(body, COMPLETE)
        self.assertEqual(final.read_bytes(), COMPLETE)
        self.assertEqual(stat.S_IMODE(final.stat().st_mode), expected_mode)
        self.assertEqual(list(cache.glob(".atomic.*")), [])

    def test_short_fixed_response_is_not_published_and_retry_recovers(self) -> None:
        with running_server(StackOrigin) as origin, self.running_proxy() as (proxy, cache):
            origin_port = int(origin.server_address[1])
            proxy_port = int(proxy.server_address[1])
            self.raw_get(proxy_port, origin_port, "recover")
            self.assertFalse((cache / "recover").exists())
            self.assertEqual(list(cache.glob(".recover.*")), [])
            status, body = self.proxy_get(proxy_port, origin_port, "recover")

        self.assertEqual(status, 200)
        self.assertEqual(body, COMPLETE)
        self.assertEqual((cache / "recover").read_bytes(), COMPLETE)
        self.assertEqual(origin.counts[f"http://127.0.0.1:{origin_port}/recover"], 2)

    def test_chunked_conflicting_length_uses_transfer_framing_not_length(self) -> None:
        with running_server(StackOrigin) as origin, self.running_proxy() as (proxy, cache):
            response = self.raw_get(
                int(proxy.server_address[1]), int(origin.server_address[1]), "chunked"
            )

        header_block, body = response.split(b"\r\n\r\n", 1)
        headers = [line.lower() for line in header_block.split(b"\r\n")]
        self.assertNotIn(b"transfer-encoding: chunked", headers)
        self.assertFalse(any(line.startswith(b"content-length:") for line in headers))
        self.assertNotIn(b"connection: close, x-hop", headers)
        self.assertNotIn(b"keep-alive: timeout=5", headers)
        self.assertNotIn(b"x-hop: remove-me", headers)
        self.assertIn(b"connection: close", headers)
        self.assertIn(b"x-end-to-end: retained", headers)
        self.assertEqual(body, CHUNKED)
        self.assertEqual((cache / "chunked").read_bytes(), CHUNKED)

    def test_response_without_declared_length_uses_eof_framing(self) -> None:
        with running_server(StackOrigin) as origin, self.running_proxy() as (proxy, cache):
            origin_port = int(origin.server_address[1])
            status, body = self.proxy_get(
                int(proxy.server_address[1]), origin_port, "nolength"
            )

        self.assertEqual(status, 200)
        self.assertEqual(body, NO_LENGTH)
        self.assertEqual((cache / "nolength").read_bytes(), NO_LENGTH)
        self.assertEqual(
            origin.counts[f"http://127.0.0.1:{origin_port}/nolength"], 1
        )

    def test_negative_declared_length_is_rejected_before_publication(self) -> None:
        with running_server(StackOrigin) as origin, self.running_proxy() as (proxy, cache):
            origin_port = int(origin.server_address[1])
            status, _body = self.proxy_get(
                int(proxy.server_address[1]), origin_port, "negative"
            )

        self.assertEqual(status, 502)
        self.assertFalse((cache / "negative").exists())
        self.assertEqual(list(cache.glob(".negative.*")), [])
        self.assertEqual(
            origin.counts[f"http://127.0.0.1:{origin_port}/negative"], 1
        )

    def test_combined_patch_contains_every_merged_core_invariant(self) -> None:
        text = self.source.read_text(encoding="utf-8")
        self.assertIn("os.O_WRONLY | os.O_CREAT | os.O_EXCL", text)
        self.assertIn("0o666", text)
        self.assertEqual(text.count("cache_destination(newpath)"), 2)
        self.assertIn("if response.chunked:", text)
        self.assertIn('blocked = blocked | {"content-length"}', text)
        self.assertIn("if not res.chunked:", text)
        self.assertIn("expected_length < 0", text)
        self.assertIn("received != expected_length", text)
        self.assertIn('self.send_header("Connection", "close")', text)


if __name__ == "__main__":
    unittest.main()
