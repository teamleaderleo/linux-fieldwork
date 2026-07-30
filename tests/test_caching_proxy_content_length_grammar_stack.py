from __future__ import annotations

import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import socketserver
import tempfile
import threading
import time
import types
import unittest


BODY = b"hello"


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def consume_headers(stream) -> None:
    while True:
        line = stream.readline()
        if line in (b"", b"\r\n", b"\n"):
            return


@contextlib.contextmanager
def running_raw_origin(content_length: str):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            consume_headers(self.rfile)
            self.server.request_count += 1
            self.wfile.write(
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {content_length}\r\n".encode("ascii")
                + b"Connection: close\r\n\r\n"
                + BODY
            )
            self.wfile.flush()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
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
            raise AssertionError("origin survived shutdown")


@contextlib.contextmanager
def running_proxy(module, old_cache: pathlib.Path, new_cache: pathlib.Path):
    old_cache.mkdir(parents=True)
    new_cache.mkdir(parents=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = False

    class Handler(module.ProxyRequestHandler):
        def log_message(self, _format, *_args):
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
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
            raise AssertionError("proxy survived shutdown")


def request(proxy, origin) -> tuple[int, bytes, list[tuple[str, str]]]:
    host = f"127.0.0.1:{origin.server_address[1]}"
    target = f"http://{host}/pool/object.deb"
    connection = http.client.HTTPConnection(
        "127.0.0.1", proxy.server_address[1], timeout=5
    )
    connection.request("GET", target, headers={"Host": host, "Connection": "close"})
    response = connection.getresponse()
    body = response.read()
    status = response.status
    headers = response.getheaders()
    connection.close()
    return status, body, headers


def wait_for_no_temporaries(directory: pathlib.Path) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        leftovers = [path for path in directory.iterdir() if path.name.startswith(".")]
        if not leftovers:
            return
        time.sleep(0.02)
    raise AssertionError(f"temporary cache entries survived: {leftovers}")


class CachingProxyContentLengthGrammarStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        composer = load_module(
            cls.repo / "investigations/caching-proxy-composed-stack/compose.py",
            "lf_content_length_grammar_composer",
        )
        cls.work = tempfile.TemporaryDirectory(prefix="cache-length-grammar-")
        cls.source = composer.compose(cls.repo, pathlib.Path(cls.work.name) / "candidate")
        cls.module = load_module(cls.source, "lf_content_length_grammar_candidate")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def test_plus_prefixed_length_is_rejected_before_commit_or_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cache-length-plus-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_raw_origin("+5") as origin, running_proxy(
                self.module, root / "old", new_cache
            ) as proxy:
                status, _body, _headers = request(proxy, origin)

            self.assertEqual(status, 502)
            self.assertEqual(origin.request_count, 1)
            final = new_cache / "pool/object.deb"
            self.assertFalse(final.exists())
            if final.parent.exists():
                wait_for_no_temporaries(final.parent)

    def test_ascii_digit_length_with_leading_zero_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cache-length-zero-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            with running_raw_origin("05") as origin, running_proxy(
                self.module, root / "old", new_cache
            ) as proxy:
                status, body, headers = request(proxy, origin)

            self.assertEqual(status, 200)
            self.assertEqual(body, BODY)
            self.assertEqual(dict(headers).get("Content-Length"), "05")
            self.assertEqual(origin.request_count, 1)
            final = new_cache / "pool/object.deb"
            self.assertEqual(final.read_bytes(), BODY)
            wait_for_no_temporaries(final.parent)

    def test_source_uses_ascii_digit_validation_before_integer_conversion(self) -> None:
        source = self.source.read_text(encoding="utf-8")
        validation = 'char < "0" or char > "9" for char in expected_length'
        self.assertIn(validation, source)
        self.assertLess(source.index(validation), source.index("expected_length = int"))


if __name__ == "__main__":
    unittest.main()
