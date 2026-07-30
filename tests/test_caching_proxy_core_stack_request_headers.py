from __future__ import annotations

import contextlib
import http.server
import importlib.util
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = ROOT / (
    "investigations/caching-proxy-core-stack/"
    "0001-compose-atomic-framing-length.patch"
)
PAYLOAD = b"composed-request-header-probe\n"


class RecordingOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.server.received.append(list(self.headers.raw_items()))
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, _format: str, *args: object) -> None:
        return


@contextlib.contextmanager
def running_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.received = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("HTTP server thread survived shutdown")


class CachingProxyCoreStackRequestHeadersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="caching-proxy-core-request-headers-"
        )
        cls.work = pathlib.Path(cls.temporary.name)
        cls.tree = cls.work / "candidate"
        cls.source = cls.tree / "upstream/mmdebstrap/caching_proxy.py"
        cls.source.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, cls.source)
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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def setUp(self) -> None:
        self.case = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.work))
        self.addCleanup(shutil.rmtree, self.case)

    def load_module(self):
        name = f"caching_proxy_core_headers_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, self.source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def running_proxy(self):
        module = self.load_module()
        module.oldcachedir = self.case / "old"
        module.newcachedir = self.case / "new"
        module.oldcachedir.mkdir()
        module.newcachedir.mkdir()
        module.readonly = False

        class QuietHandler(module.ProxyRequestHandler):
            def log_message(self, _format: str, *args: object) -> None:
                return

        with running_server(QuietHandler) as server:
            yield server

    @staticmethod
    def raw_request(proxy_port: int, target: str, headers: list[str]) -> bytes:
        request = (
            f"GET {target} HTTP/1.1\r\n"
            + "\r\n".join(headers)
            + "\r\n\r\n"
        ).encode("ascii")
        with socket.create_connection(("127.0.0.1", proxy_port), timeout=5) as client:
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
    def values(headers: list[tuple[str, str]], name: str) -> list[str]:
        lowered = name.lower()
        return [value for key, value in headers if key.lower() == lowered]

    def test_composed_source_filters_proxy_hop_fields_and_preserves_duplicates(self) -> None:
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/headers"
            request_headers = [
                f"Host: {host}",
                "pRoXy-AuThOrIzAtIoN: Basic fake-proxy-credential",
                "Proxy-Connection: keep-alive",
                "Connection: close, X-Hop",
                "Keep-Alive: timeout=60",
                "TE: trailers",
                "Trailer: X-Trailer",
                "Transfer-Encoding: identity",
                "Upgrade: h2c",
                "X-Hop: remove-me",
                "X-Safe: first",
                "X-Safe: second",
                "Range: bytes=0-10",
                'If-None-Match: "fake-etag"',
                "Accept: application/octet-stream",
                "Content-Length: 0",
            ]
            with self.running_proxy() as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, request_headers
                )

        self.assertTrue(response.startswith(b"HTTP/1.1 200 OK\r\n"), response[:80])
        self.assertEqual(response.split(b"\r\n\r\n", 1)[1], PAYLOAD)
        self.assertEqual(len(origin.received), 1)
        received = origin.received[0]
        for blocked in (
            "Proxy-Authorization",
            "Proxy-Connection",
            "Keep-Alive",
            "TE",
            "Trailer",
            "Transfer-Encoding",
            "Upgrade",
            "X-Hop",
        ):
            with self.subTest(blocked=blocked):
                self.assertEqual(self.values(received, blocked), [])
        self.assertEqual(self.values(received, "Connection"), ["close"])
        self.assertEqual(self.values(received, "Host"), [host])
        self.assertEqual(self.values(received, "X-Safe"), ["first", "second"])
        self.assertEqual(self.values(received, "Range"), ["bytes=0-10"])
        self.assertEqual(self.values(received, "If-None-Match"), ['"fake-etag"'])
        self.assertEqual(
            self.values(received, "Accept"), ["application/octet-stream"]
        )

    def test_composed_source_rejects_duplicate_host_before_origin_contact(self) -> None:
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/duplicate-host"
            headers = [
                f"Host: {host}",
                f"Host: {host}",
                "Connection: close",
                "Content-Length: 0",
            ]
            with self.running_proxy() as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, headers
                )

        self.assertTrue(response.startswith(b"HTTP/1.0 400 "), response[:80])
        self.assertEqual(origin.received, [])

    def test_composed_source_contains_request_and_response_invariants(self) -> None:
        text = self.source.read_text(encoding="utf-8")
        self.assertIn("def origin_request_headers(headers):", text)
        self.assertIn("headers.raw_items()", text)
        self.assertIn('headers.get_all("Connection", [])', text)
        self.assertNotIn("dict(self.headers)", text)
        self.assertIn("def downstream_headers(response):", text)
        self.assertIn("def cache_destination(path):", text)
        self.assertIn("if not res.chunked:", text)


if __name__ == "__main__":
    unittest.main()
