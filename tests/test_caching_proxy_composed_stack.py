from __future__ import annotations

import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import socketserver
import stat
import tempfile
import threading
import time
import types
import unittest


PAYLOAD = b"A" * (128 * 1024)
SHORT = PAYLOAD[: 64 * 1024]
CHUNKED = b"chunk-one-chunk-two"


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def running_http_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.request_count = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
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
        "127.0.0.1", proxy.server_address[1], timeout=5
    )
    connection.request(
        "GET", target, headers={"Host": host, "Connection": "close"}
    )
    return connection, connection.getresponse()


def wait_for_no_temporaries(directory: pathlib.Path) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        temporary = [path for path in directory.iterdir() if path.name.startswith(".")]
        if not temporary:
            return
        time.sleep(0.02)
    raise AssertionError(f"temporary cache files survived: {temporary}")


class FixedOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.send_header("X-End-To-End", "preserved")
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, _format, *_args):
        return


class RecoveringShortOrigin(socketserver.StreamRequestHandler):
    def handle(self):
        self.rfile.readuntil(b"\r\n\r\n")
        with self.server.lock:
            self.server.request_count += 1
            request_number = self.server.request_count
        body = SHORT if request_number == 1 else PAYLOAD
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            + f"Content-Length: {len(PAYLOAD)}\r\n".encode()
            + b"Connection: close\r\n\r\n"
            + body
        )
        self.wfile.flush()


class ChunkedOrigin(socketserver.StreamRequestHandler):
    def handle(self):
        self.rfile.readuntil(b"\r\n\r\n")
        with self.server.lock:
            self.server.request_count += 1
        first = CHUNKED[:9]
        second = CHUNKED[9:]
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Length: 999\r\n"
            b"Connection: close, X-Hop\r\n"
            b"X-Hop: remove-me\r\n"
            b"X-End-To-End: keep-me\r\n\r\n"
            + f"{len(first):X}\r\n".encode()
            + first
            + b"\r\n"
            + f"{len(second):X}\r\n".encode()
            + second
            + b"\r\n0\r\n\r\n"
        )
        self.wfile.flush()


class CachingProxyComposedStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        composer_path = cls.repo / (
            "investigations/caching-proxy-composed-stack/compose.py"
        )
        cls.composer = load_module(composer_path, "lf_caching_proxy_composer")
        cls.work = tempfile.TemporaryDirectory(prefix="caching-proxy-stack-")
        cls.candidate = cls.composer.compose(
            cls.repo, pathlib.Path(cls.work.name) / "candidate"
        )
        cls.module = load_module(cls.candidate, "lf_caching_proxy_composed")

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_manifest_and_source_contract(self):
        self.assertEqual(
            self.composer.REQUIRED_REPAIRS,
            (
                "investigations/caching-proxy-atomic-publication/0001-publish-cache-files-atomically.patch",
                "investigations/caching-proxy-hop-by-hop-framing/0001-normalize-downstream-framing.patch",
                "investigations/caching-proxy-content-length/0001-reject-short-upstream-responses.patch",
            ),
        )
        for relative in self.composer.REQUIRED_REPAIRS:
            self.assertTrue((self.repo / relative).is_file(), relative)
        source = self.candidate.read_text(encoding="utf-8")
        self.assertEqual(source.count("cache_destination(newpath)"), 2)
        self.assertIn("headers = downstream_headers(res)", source)
        self.assertIn("expected_length = None if res.chunked else", source)
        self.assertIn("received != expected_length", source)
        self.assertIn("os.O_CREAT | os.O_EXCL", source)
        self.assertIn("0o666", source)

    def test_fixed_length_fill_preserves_body_headers_mode_and_cache(self):
        with tempfile.TemporaryDirectory(prefix="caching-proxy-fixed-") as tmp:
            root = pathlib.Path(tmp)
            control = root / "control"
            control.write_bytes(b"control")
            with running_http_server(FixedOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/package.deb"
                new_cache = root / "new"
                with running_proxy(self.module, root / "old", new_cache) as proxy:
                    connection, response = proxy_request(proxy, target, host)
                    body = response.read()
                    headers = {name.lower(): value for name, value in response.getheaders()}
                    connection.close()
            cached = new_cache / "pool/package.deb"
            self.assertEqual(response.status, 200)
            self.assertEqual(body, PAYLOAD)
            self.assertEqual(cached.read_bytes(), PAYLOAD)
            self.assertEqual(headers["content-length"], str(len(PAYLOAD)))
            self.assertEqual(headers["x-end-to-end"], "preserved")
            self.assertEqual(headers["connection"].lower(), "close")
            self.assertEqual(
                stat.S_IMODE(cached.stat().st_mode),
                stat.S_IMODE(control.stat().st_mode),
            )
            wait_for_no_temporaries(cached.parent)

    def test_short_declared_response_is_not_published_and_retry_recovers(self):
        with tempfile.TemporaryDirectory(prefix="caching-proxy-short-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_raw_server(RecoveringShortOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/package.deb"
                with running_proxy(self.module, root / "old", new_cache) as proxy:
                    connection, response = proxy_request(proxy, target, host)
                    try:
                        response.read()
                    except http.client.IncompleteRead:
                        pass
                    connection.close()
                    final = new_cache / "pool/package.deb"
                    wait_for_no_temporaries(final.parent)
                    self.assertFalse(final.exists())

                    connection, response = proxy_request(proxy, target, host)
                    body = response.read()
                    connection.close()

            self.assertEqual(body, PAYLOAD)
            self.assertEqual(final.read_bytes(), PAYLOAD)
            self.assertEqual(origin.request_count, 2)
            wait_for_no_temporaries(final.parent)

    def test_chunked_conflicting_length_is_decoded_and_not_length_validated(self):
        with tempfile.TemporaryDirectory(prefix="caching-proxy-chunked-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_raw_server(ChunkedOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/chunked.deb"
                with running_proxy(self.module, root / "old", new_cache) as proxy:
                    connection, response = proxy_request(proxy, target, host)
                    body = response.read()
                    headers = {name.lower(): value for name, value in response.getheaders()}
                    connection.close()

            self.assertEqual(response.status, 200)
            self.assertEqual(body, CHUNKED)
            self.assertNotIn("transfer-encoding", headers)
            self.assertNotIn("content-length", headers)
            self.assertNotIn("x-hop", headers)
            self.assertEqual(headers["x-end-to-end"], "keep-me")
            self.assertEqual(headers["connection"].lower(), "close")
            cached = new_cache / "pool/chunked.deb"
            self.assertEqual(cached.read_bytes(), CHUNKED)
            self.assertEqual(origin.request_count, 1)
            wait_for_no_temporaries(cached.parent)


if __name__ == "__main__":
    unittest.main()
