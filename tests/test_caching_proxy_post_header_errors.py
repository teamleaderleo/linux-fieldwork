from __future__ import annotations

import contextlib
import http.server
import importlib.util
import io
import pathlib
import socket
import socketserver
import tempfile
import threading
import time
import types
import unittest


PAYLOAD = b"complete-origin-payload\n"
SHORT = b"short"


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
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("HTTP server survived shutdown")


@contextlib.contextmanager
def running_raw_server(handler):
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("raw origin survived shutdown")


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


def raw_proxy_request(proxy_port: int, target: str, host: str) -> bytes:
    request = (
        f"GET {target} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n"
        "Content-Length: 0\r\n\r\n"
    ).encode("ascii")
    with socket.create_connection(("127.0.0.1", proxy_port), timeout=5) as client:
        client.settimeout(5)
        client.sendall(request)
        response = bytearray()
        while True:
            block = client.recv(65536)
            if not block:
                break
            response.extend(block)
    return bytes(response)


def unused_loopback_port() -> int:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    return port


def wait_for_clean_cache(directory: pathlib.Path, final: pathlib.Path) -> None:
    deadline = time.monotonic() + 5
    leftovers = []
    while time.monotonic() < deadline:
        leftovers = [
            path for path in directory.iterdir() if path.name.startswith(".")
        ]
        if not final.exists() and not leftovers:
            return
        time.sleep(0.02)
    raise AssertionError(
        f"failed cache state survived: final={final.exists()} temporary={leftovers}"
    )


class ShortOrigin(socketserver.StreamRequestHandler):
    def handle(self):
        self.rfile.readuntil(b"\r\n\r\n")
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 20\r\n"
            b"Connection: close\r\n\r\n"
            + SHORT
        )
        self.wfile.flush()


class FixedOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, _format, *_args):
        return


class CachingProxyPostHeaderErrorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        base_composer = load_module(
            cls.repo / "investigations/caching-proxy-composed-stack/compose.py",
            "lf_proxy_base_stack_composer",
        )
        candidate_composer = load_module(
            cls.repo / "investigations/caching-proxy-post-header-errors/compose.py",
            "lf_proxy_post_header_composer",
        )
        cls.work = tempfile.TemporaryDirectory(prefix="proxy-post-header-")
        work = pathlib.Path(cls.work.name)
        cls.base_source = base_composer.compose(cls.repo, work / "base")
        cls.candidate_source = candidate_composer.compose(
            cls.repo, work / "candidate"
        )
        cls.base = load_module(cls.base_source, "lf_proxy_post_header_base")
        cls.candidate = load_module(
            cls.candidate_source, "lf_proxy_post_header_candidate"
        )

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_source_contract_tracks_commitment_and_preserves_preheader_502(self):
        source = self.candidate_source.read_text(encoding="utf-8")
        self.assertIn("response_started = False", source)
        self.assertIn("response_started = True", source)
        self.assertIn("if response_started:", source)
        self.assertIn("self.close_connection = True", source)
        self.assertIn("self.send_error(502)", source)
        self.assertIn("proxy request failed:", source)

    def test_baseline_appends_502_after_started_200_but_candidate_does_not(self):
        with tempfile.TemporaryDirectory(prefix="proxy-post-header-short-") as tmp:
            root = pathlib.Path(tmp)
            with running_raw_server(ShortOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/short.deb"
                results = {}
                for label, module in (
                    ("base", self.base),
                    ("candidate", self.candidate),
                ):
                    new_cache = root / label / "new"
                    error_log = io.StringIO()
                    with contextlib.redirect_stderr(error_log):
                        with running_proxy(
                            module, root / label / "old", new_cache
                        ) as proxy:
                            response = raw_proxy_request(
                                int(proxy.server_address[1]), target, host
                            )
                    final = new_cache / "pool/short.deb"
                    wait_for_clean_cache(final.parent, final)
                    results[label] = (response, error_log.getvalue())

            base_response, _base_log = results["base"]
            candidate_response, candidate_log = results["candidate"]
            self.assertTrue(base_response.startswith(b"HTTP/1.1 200 OK\r\n"))
            self.assertGreaterEqual(base_response.count(b"HTTP/"), 2)
            self.assertIn(b"502 Bad Gateway", base_response)

            self.assertTrue(candidate_response.startswith(b"HTTP/1.1 200 OK\r\n"))
            self.assertEqual(candidate_response.count(b"HTTP/"), 1)
            self.assertNotIn(b"502 Bad Gateway", candidate_response)
            self.assertIn("IncompleteRead", candidate_log)

    def test_failure_before_commit_still_returns_one_normal_502(self):
        with tempfile.TemporaryDirectory(prefix="proxy-preheader-") as tmp:
            root = pathlib.Path(tmp)
            port = unused_loopback_port()
            host = f"127.0.0.1:{port}"
            target = f"http://{host}/pool/unreachable.deb"
            error_log = io.StringIO()
            with contextlib.redirect_stderr(error_log):
                with running_proxy(
                    self.candidate, root / "old", root / "new"
                ) as proxy:
                    response = raw_proxy_request(
                        int(proxy.server_address[1]), target, host
                    )

            self.assertTrue(response.startswith(b"HTTP/1.0 502"))
            self.assertEqual(response.count(b"HTTP/"), 1)
            self.assertIn("ConnectionRefusedError", error_log.getvalue())

    def test_cache_writer_failure_closes_started_response_without_second_status(self):
        with tempfile.TemporaryDirectory(prefix="proxy-writer-error-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            original_destination = self.candidate.cache_destination

            class FailingWriter:
                def write(self, _data):
                    raise OSError("injected cache writer failure")

            @contextlib.contextmanager
            def failing_destination(_path):
                yield FailingWriter()

            self.candidate.cache_destination = failing_destination
            try:
                with running_http_server(FixedOrigin) as origin:
                    host = f"127.0.0.1:{origin.server_address[1]}"
                    target = f"http://{host}/pool/writer.deb"
                    error_log = io.StringIO()
                    with contextlib.redirect_stderr(error_log):
                        with running_proxy(
                            self.candidate, root / "old", new_cache
                        ) as proxy:
                            response = raw_proxy_request(
                                int(proxy.server_address[1]), target, host
                            )
            finally:
                self.candidate.cache_destination = original_destination

            self.assertTrue(response.startswith(b"HTTP/1.1 200 OK\r\n"))
            self.assertEqual(response.count(b"HTTP/"), 1)
            self.assertNotIn(b"502 Bad Gateway", response)
            self.assertIn("injected cache writer failure", error_log.getvalue())
            final = new_cache / "pool/writer.deb"
            self.assertFalse(final.exists())


if __name__ == "__main__":
    unittest.main()
