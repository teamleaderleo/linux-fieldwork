from __future__ import annotations

import concurrent.futures
import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import socket
import socketserver
import stat
import tempfile
import threading
import time
import types
import unittest


PAYLOAD = b"A" * (128 * 1024)
SHORT = PAYLOAD[: 64 * 1024]
NO_LENGTH = b"eof-framed-payload\n"
NEGATIVE_LENGTH = b"negative-length-payload\n"


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_request_headers(stream) -> None:
    while True:
        line = stream.readline()
        if line in (b"", b"\r\n", b"\n"):
            return


@contextlib.contextmanager
def running_http_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.request_count = 0
    server.lock = threading.Lock()
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
            raise AssertionError("HTTP server did not stop")


@contextlib.contextmanager
def running_raw_server(handler):
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), handler)
    server.request_count = 0
    server.lock = threading.Lock()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("raw HTTP server did not stop")


@contextlib.contextmanager
def running_proxy(module, old_cache: pathlib.Path, new_cache: pathlib.Path):
    old_cache.mkdir(parents=True, exist_ok=True)
    new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = False

    class QuietProxy(module.ProxyRequestHandler):
        def log_message(self, _format, *_args):
            return

    with running_http_server(QuietProxy) as server:
        yield server


def proxy_request(proxy, target: str, host: str):
    connection = http.client.HTTPConnection(
        "127.0.0.1", proxy.server_address[1], timeout=10
    )
    connection.request(
        "GET", target, headers={"Host": host, "Connection": "close"}
    )
    response = connection.getresponse()
    return connection, response


def raw_proxy_request(proxy, target: str, host: str) -> bytes:
    request = (
        f"GET {target} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")
    with socket.create_connection(
        ("127.0.0.1", proxy.server_address[1]), timeout=5
    ) as client:
        client.settimeout(10)
        client.sendall(request)
        result = bytearray()
        while True:
            block = client.recv(65536)
            if not block:
                break
            result.extend(block)
    return bytes(result)


def wait_for_no_temporaries(directory: pathlib.Path) -> None:
    deadline = time.monotonic() + 5
    temporary: list[pathlib.Path] = []
    while time.monotonic() < deadline:
        temporary = [path for path in directory.iterdir() if path.name.startswith(".")]
        if not temporary:
            return
        time.sleep(0.02)
    raise AssertionError(f"temporary cache files survived: {temporary}")


class AtomicOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with self.server.lock:
            self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(SHORT)
        self.wfile.flush()
        self.server.atomic_started.set()
        if self.server.atomic_release.wait(timeout=10):
            self.wfile.write(PAYLOAD[len(SHORT) :])
            self.wfile.flush()

    def log_message(self, _format, *_args):
        return


class NoLengthOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with self.server.lock:
            self.server.request_count += 1
        self.send_response(200)
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(NO_LENGTH)
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, _format, *_args):
        return


class NegativeLengthOrigin(socketserver.StreamRequestHandler):
    def handle(self):
        read_request_headers(self.rfile)
        with self.server.lock:
            self.server.request_count += 1
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: -1\r\n"
            b"Connection: close\r\n\r\n"
            + NEGATIVE_LENGTH
        )
        self.wfile.flush()


class CachingProxyComposedStackExtendedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        composer_path = cls.repo / (
            "investigations/caching-proxy-composed-stack/compose.py"
        )
        cls.composer = load_module(
            composer_path, "lf_caching_proxy_extended_composer"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="caching-proxy-extended-")
        cls.candidate = cls.composer.compose(
            cls.repo, pathlib.Path(cls.work.name) / "candidate"
        )
        cls.module = load_module(
            cls.candidate, "lf_caching_proxy_composed_extended"
        )

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_atomic_publication_hides_final_name_for_concurrent_misses(self):
        with tempfile.TemporaryDirectory(prefix="proxy-atomic-stack-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            control = root / "mode-control"
            control.write_bytes(b"control")
            expected_mode = stat.S_IMODE(control.stat().st_mode)

            with running_http_server(AtomicOrigin) as origin, running_proxy(
                self.module, root / "old", new_cache
            ) as proxy, concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/atomic.deb"
                first = pool.submit(proxy_request, proxy, target, host)
                self.assertTrue(origin.atomic_started.wait(timeout=5))
                final = new_cache / "pool/atomic.deb"
                self.assertFalse(final.exists())

                second = pool.submit(proxy_request, proxy, target, host)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    with origin.lock:
                        if origin.request_count >= 2:
                            break
                    time.sleep(0.02)
                else:
                    raise AssertionError("second miss did not reach origin")
                self.assertFalse(final.exists())
                origin.atomic_release.set()

                responses = []
                for future in (first, second):
                    connection, response = future.result(timeout=10)
                    responses.append((response.status, response.read()))
                    connection.close()

            self.assertEqual(responses, [(200, PAYLOAD), (200, PAYLOAD)])
            self.assertEqual(final.read_bytes(), PAYLOAD)
            self.assertEqual(stat.S_IMODE(final.stat().st_mode), expected_mode)
            wait_for_no_temporaries(final.parent)

    def test_response_without_length_uses_eof_framing_and_caches(self):
        with tempfile.TemporaryDirectory(prefix="proxy-no-length-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_http_server(NoLengthOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/nolength.deb"
                with running_proxy(self.module, root / "old", new_cache) as proxy:
                    connection, response = proxy_request(proxy, target, host)
                    body = response.read()
                    headers = {
                        name.lower(): value for name, value in response.getheaders()
                    }
                    connection.close()

            self.assertEqual(response.status, 200)
            self.assertEqual(body, NO_LENGTH)
            self.assertNotIn("content-length", headers)
            self.assertEqual(headers["connection"].lower(), "close")
            cached = new_cache / "pool/nolength.deb"
            self.assertEqual(cached.read_bytes(), NO_LENGTH)
            self.assertEqual(origin.request_count, 1)
            wait_for_no_temporaries(cached.parent)

    def test_negative_declared_length_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory(prefix="proxy-negative-length-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_raw_server(NegativeLengthOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/negative.deb"
                with running_proxy(self.module, root / "old", new_cache) as proxy:
                    response = raw_proxy_request(proxy, target, host)

            self.assertTrue(response.startswith(b"HTTP/1.0 502"), response[:80])
            self.assertEqual(response.count(b"HTTP/"), 1)
            final = new_cache / "pool/negative.deb"
            self.assertFalse(final.exists())
            self.assertEqual(origin.request_count, 1)
            if final.parent.exists():
                wait_for_no_temporaries(final.parent)

    def test_composed_source_retains_negative_length_guard(self):
        source = self.candidate.read_text(encoding="utf-8")
        self.assertIn("if expected_length < 0", source)
        self.assertIn("negative upstream Content-Length", source)
        self.assertIn(
            "expected_length < 0",
            self.composer.REQUIRED_PATCH_MARKERS[
                self.composer.REQUIRED_REPAIRS[2]
            ],
        )


if __name__ == "__main__":
    unittest.main()
