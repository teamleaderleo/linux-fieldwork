from __future__ import annotations

import contextlib
import importlib.util
import pathlib
import socket
import socketserver
import tempfile
import threading
import types
import unittest


UNSUPPORTED_BODY = b"encoded-transfer-representation\n"


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


class GzipTransferOrigin(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        read_request_headers(self.rfile)
        self.server.request_count += 1
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: gzip\r\n"
            b"Connection: close\r\n\r\n"
            + UNSUPPORTED_BODY
        )
        self.wfile.flush()


class CompoundTransferOrigin(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        read_request_headers(self.rfile)
        self.server.request_count += 1
        self.wfile.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: gzip, chunked\r\n"
            b"Connection: close\r\n\r\n"
            b"5\r\nshort\r\n0\r\n\r\n"
        )
        self.wfile.flush()


@contextlib.contextmanager
def running_raw_server(handler):
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), handler)
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
            raise AssertionError("raw origin thread survived shutdown")


@contextlib.contextmanager
def running_proxy(module, old_cache: pathlib.Path, new_cache: pathlib.Path):
    import http.server

    old_cache.mkdir(parents=True, exist_ok=True)
    new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = False

    class QuietProxy(module.ProxyRequestHandler):
        def log_message(self, _format, *_args):
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietProxy)
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
            raise AssertionError("proxy thread survived shutdown")


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
        response = bytearray()
        while True:
            block = client.recv(65536)
            if not block:
                break
            response.extend(block)
    return bytes(response)


class CachingProxyTransferCodingRejectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        composer = load_module(
            cls.repo / "investigations/caching-proxy-composed-stack/compose.py",
            "lf_transfer_coding_composer",
        )
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="caching-proxy-transfer-coding-"
        )
        cls.candidate = composer.compose(
            cls.repo, pathlib.Path(cls.temporary.name) / "candidate"
        )
        cls.module = load_module(cls.candidate, "lf_transfer_coding_candidate")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_unsupported_transfer_codings_fail_before_commit_or_cache(self) -> None:
        for label, handler in (
            ("gzip", GzipTransferOrigin),
            ("gzip-chunked", CompoundTransferOrigin),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix=f"proxy-{label}-"
            ) as tmp:
                root = pathlib.Path(tmp)
                new_cache = root / "new"
                with running_raw_server(handler) as origin:
                    host = f"127.0.0.1:{origin.server_address[1]}"
                    target = f"http://{host}/pool/{label}.deb"
                    with running_proxy(
                        self.module, root / "old", new_cache
                    ) as proxy:
                        response = raw_proxy_request(proxy, target, host)

                self.assertTrue(response.startswith(b"HTTP/1.0 502"), response[:100])
                self.assertEqual(response.count(b"HTTP/"), 1, response)
                self.assertNotIn(UNSUPPORTED_BODY, response)
                self.assertEqual(origin.request_count, 1)
                final = new_cache / f"pool/{label}.deb"
                self.assertFalse(final.exists())
                if final.parent.exists():
                    self.assertEqual(
                        [path for path in final.parent.iterdir() if path.name.startswith(".")],
                        [],
                    )

    def test_exact_chunked_coding_remains_the_only_supported_transfer_coding(self) -> None:
        source = self.candidate.read_text(encoding="utf-8")
        self.assertIn('values = response.headers.get_all("Transfer-Encoding", [])', source)
        self.assertIn('if tokens != ["chunked"] or not response.chunked:', source)
        self.assertIn("unsupported upstream Transfer-Encoding", source)
        fresh = source.index("res = conn.getresponse()")
        validation = source.index("validate_transfer_encoding(res)", fresh)
        commitment = source.index('self.wfile.write(b"HTTP/1.1 200 OK', fresh)
        self.assertLess(validation, commitment)


if __name__ == "__main__":
    unittest.main()
