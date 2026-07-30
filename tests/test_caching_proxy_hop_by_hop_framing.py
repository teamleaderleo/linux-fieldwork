from __future__ import annotations

import contextlib
import http.client
import importlib.util
import pathlib
import shutil
import socket
import socketserver
import subprocess
import tempfile
import threading
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = ROOT / (
    "investigations/caching-proxy-hop-by-hop-framing/"
    "0001-normalize-downstream-framing.patch"
)
CHUNKED_PAYLOAD = b"payload-without-chunk-framing\n"
FIXED_PAYLOAD = b"fixed-length-payload\n"


class UpstreamServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.request_count = 0


class UpstreamHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        request = bytearray()
        while b"\r\n\r\n" not in request:
            block = self.request.recv(4096)
            if not block:
                return
            request.extend(block)
        self.server.request_count += 1
        first_line = bytes(request).split(b"\r\n", 1)[0]
        if b"/chunked" in first_line:
            self.request.sendall(
                b"HTTP/1.1 200 OK\r\n"
                b"Transfer-Encoding: chunked\r\n"
                b"Content-Length: 999\r\n"
                b"Connection: close, X-Hop\r\n"
                b"Keep-Alive: timeout=5\r\n"
                b"Trailer: X-Trailer\r\n"
                b"X-Hop: remove-me\r\n"
                b"X-End-To-End: retained\r\n"
                b"\r\n"
            )
            chunks = (CHUNKED_PAYLOAD[:9], CHUNKED_PAYLOAD[9:])
            for chunk in chunks:
                self.request.sendall(f"{len(chunk):X}\r\n".encode("ascii"))
                self.request.sendall(chunk + b"\r\n")
            self.request.sendall(b"0\r\nX-Trailer: trailer-value\r\n\r\n")
            return
        if b"/fixed" in first_line:
            self.request.sendall(
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(FIXED_PAYLOAD)}\r\n".encode("ascii")
                + b"Connection: close, X-Hop\r\n"
                + b"X-Hop: remove-me\r\n"
                + b"X-End-To-End: retained\r\n"
                + b"\r\n"
                + FIXED_PAYLOAD
            )
            return
        self.request.sendall(
            b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        )


class CachingProxyHopByHopFramingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="caching-proxy-framing-")
        self.addCleanup(self.tempdir.cleanup)
        self.work = pathlib.Path(self.tempdir.name)

    def prepare_source(self, *, patched: bool) -> pathlib.Path:
        tree = self.work / ("patched" if patched else "baseline")
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

    @staticmethod
    def load_module(source: pathlib.Path):
        name = f"caching_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def running_upstream(self):
        server = UpstreamServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    @contextlib.contextmanager
    def running_proxy(self, source: pathlib.Path, label: str):
        module = self.load_module(source)
        old_cache = self.work / label / "old"
        new_cache = self.work / label / "new"
        old_cache.mkdir(parents=True)
        new_cache.mkdir(parents=True)
        module.oldcachedir = old_cache
        module.newcachedir = new_cache
        module.readonly = False

        class QuietHandler(module.ProxyRequestHandler):
            def log_message(self, _format, *args):
                return None

        server = module.http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), QuietHandler
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server, new_cache
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())

    @staticmethod
    def raw_request(proxy_port: int, upstream_port: int, path: str) -> bytes:
        upstream = f"127.0.0.1:{upstream_port}"
        absolute = f"http://{upstream}/{path}"
        request = (
            f"GET {absolute} HTTP/1.1\r\n"
            f"Host: {upstream}\r\n"
            "Connection: close\r\n"
            "\r\n"
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
    def split_response(response: bytes) -> tuple[list[bytes], bytes]:
        header_block, body = response.split(b"\r\n\r\n", 1)
        return header_block.split(b"\r\n"), body

    def test_baseline_forwards_chunked_header_after_dechunking_body(self) -> None:
        source = self.prepare_source(patched=False)
        with self.running_upstream() as upstream:
            upstream_port = int(upstream.server_address[1])
            with self.running_proxy(source, "baseline") as (proxy, new_cache):
                response = self.raw_request(
                    int(proxy.server_address[1]), upstream_port, "chunked"
                )

        headers, body = self.split_response(response)
        lowered = [line.lower() for line in headers]
        self.assertIn(b"transfer-encoding: chunked", lowered)
        self.assertIn(b"content-length: 999", lowered)
        self.assertIn(b"connection: close, x-hop", lowered)
        self.assertIn(b"keep-alive: timeout=5", lowered)
        self.assertIn(b"trailer: x-trailer", lowered)
        self.assertIn(b"x-hop: remove-me", lowered)
        self.assertEqual(body, CHUNKED_PAYLOAD)
        self.assertEqual((new_cache / "chunked").read_bytes(), CHUNKED_PAYLOAD)

    def test_candidate_normalizes_chunked_response_and_hop_headers(self) -> None:
        source = self.prepare_source(patched=True)
        with self.running_upstream() as upstream:
            upstream_port = int(upstream.server_address[1])
            with self.running_proxy(source, "candidate") as (proxy, new_cache):
                response = self.raw_request(
                    int(proxy.server_address[1]), upstream_port, "chunked"
                )

        headers, body = self.split_response(response)
        lowered = [line.lower() for line in headers]
        self.assertNotIn(b"transfer-encoding: chunked", lowered)
        self.assertFalse(any(line.startswith(b"content-length:") for line in lowered))
        self.assertNotIn(b"connection: close, x-hop", lowered)
        self.assertNotIn(b"keep-alive: timeout=5", lowered)
        self.assertNotIn(b"trailer: x-trailer", lowered)
        self.assertNotIn(b"x-hop: remove-me", lowered)
        self.assertIn(b"connection: close", lowered)
        self.assertIn(b"x-end-to-end: retained", lowered)
        self.assertEqual(body, CHUNKED_PAYLOAD)
        self.assertEqual((new_cache / "chunked").read_bytes(), CHUNKED_PAYLOAD)

    def test_candidate_chunked_response_is_readable_by_http_client(self) -> None:
        source = self.prepare_source(patched=True)
        with self.running_upstream() as upstream:
            upstream_port = int(upstream.server_address[1])
            upstream_host = f"127.0.0.1:{upstream_port}"
            absolute = f"http://{upstream_host}/chunked"
            with self.running_proxy(source, "http-client") as (proxy, _new_cache):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", int(proxy.server_address[1]), timeout=5
                )
                connection.putrequest(
                    "GET", absolute, skip_host=True, skip_accept_encoding=True
                )
                connection.putheader("Host", upstream_host)
                connection.putheader("Connection", "close")
                connection.endheaders()
                response = connection.getresponse()
                body = response.read()
                connection.close()

        self.assertEqual(response.status, 200)
        self.assertIsNone(response.getheader("Transfer-Encoding"))
        self.assertIsNone(response.getheader("Content-Length"))
        self.assertEqual(response.getheader("Connection"), "close")
        self.assertEqual(body, CHUNKED_PAYLOAD)

    def test_candidate_preserves_fixed_length_end_to_end_headers(self) -> None:
        source = self.prepare_source(patched=True)
        with self.running_upstream() as upstream:
            upstream_port = int(upstream.server_address[1])
            with self.running_proxy(source, "fixed") as (proxy, new_cache):
                response = self.raw_request(
                    int(proxy.server_address[1]), upstream_port, "fixed"
                )

        headers, body = self.split_response(response)
        lowered = [line.lower() for line in headers]
        self.assertIn(
            f"content-length: {len(FIXED_PAYLOAD)}".encode("ascii"), lowered
        )
        self.assertIn(b"connection: close", lowered)
        self.assertNotIn(b"connection: close, x-hop", lowered)
        self.assertNotIn(b"x-hop: remove-me", lowered)
        self.assertIn(b"x-end-to-end: retained", lowered)
        self.assertEqual(body, FIXED_PAYLOAD)
        self.assertEqual((new_cache / "fixed").read_bytes(), FIXED_PAYLOAD)


if __name__ == "__main__":
    unittest.main()
