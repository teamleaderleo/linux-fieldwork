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
    "investigations/caching-proxy-request-hop-headers/"
    "0001-filter-origin-request-headers.patch"
)
PAYLOAD = b"origin-header-probe\n"


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


class QuietProxyMixin:
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


class CachingProxyRequestHopHeadersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="caching-proxy-request-headers-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)

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

    @staticmethod
    def load_module(path: pathlib.Path):
        name = f"caching_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def running_proxy(self, source: pathlib.Path, label: str):
        module = self.load_module(source)
        module.oldcachedir = self.work / label / "old"
        module.newcachedir = self.work / label / "new"
        module.oldcachedir.mkdir(parents=True)
        module.newcachedir.mkdir(parents=True)
        module.readonly = False

        class QuietProxy(QuietProxyMixin, module.ProxyRequestHandler):
            pass

        with running_server(QuietProxy) as server:
            yield server

    @staticmethod
    def raw_request(
        proxy_port: int,
        target: str,
        header_lines: list[str],
    ) -> bytes:
        request = (
            f"GET {target} HTTP/1.1\r\n"
            + "\r\n".join(header_lines)
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
    def status(response: bytes) -> int:
        status_line = response.split(b"\r\n", 1)[0]
        return int(status_line.split(b" ", 2)[1])

    @staticmethod
    def header_values(raw_headers, name: str) -> list[str]:
        lowered = name.lower()
        return [value for key, value in raw_headers if key.lower() == lowered]

    def request_headers(self, host: str) -> list[str]:
        return [
            f"Host: {host}",
            "pRoXy-AuThOrIzAtIoN: Basic fake-proxy-credential",
            "Proxy-Connection: keep-alive",
            "cOnNeCtIoN: close, X-Hop",
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

    def test_baseline_leaks_proxy_and_connection_headers_to_origin(self) -> None:
        source = self.prepare_source(patched=False)
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/package.deb"
            with self.running_proxy(source, "baseline") as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, self.request_headers(host)
                )

        self.assertEqual(self.status(response), 200)
        self.assertEqual(len(origin.received), 1)
        headers = origin.received[0]
        self.assertEqual(
            self.header_values(headers, "Proxy-Authorization"),
            ["Basic fake-proxy-credential"],
        )
        self.assertEqual(self.header_values(headers, "X-Hop"), ["remove-me"])
        self.assertEqual(
            self.header_values(headers, "Connection"), ["close, X-Hop"]
        )
        self.assertTrue(self.header_values(headers, "Proxy-Connection"))
        self.assertNotEqual(self.header_values(headers, "X-Safe"), ["first", "second"])

    def test_candidate_filters_hop_headers_and_preserves_safe_duplicates(self) -> None:
        source = self.prepare_source(patched=True)
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/package.deb"
            with self.running_proxy(source, "candidate") as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, self.request_headers(host)
                )

        self.assertEqual(self.status(response), 200)
        self.assertEqual(len(origin.received), 1)
        headers = origin.received[0]
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
                self.assertEqual(self.header_values(headers, blocked), [])
        self.assertEqual(self.header_values(headers, "Connection"), ["close"])
        self.assertEqual(self.header_values(headers, "Host"), [host])
        self.assertEqual(self.header_values(headers, "X-Safe"), ["first", "second"])
        self.assertEqual(self.header_values(headers, "Range"), ["bytes=0-10"])
        self.assertEqual(self.header_values(headers, "If-None-Match"), ['"fake-etag"'])
        self.assertEqual(
            self.header_values(headers, "Accept"), ["application/octet-stream"]
        )

    def test_candidate_rejects_connection_token_that_names_host(self) -> None:
        source = self.prepare_source(patched=True)
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/package.deb"
            headers = [
                f"Host: {host}",
                "Connection: close, Host",
                "Content-Length: 0",
            ]
            with self.running_proxy(source, "host-token") as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, headers
                )

        self.assertEqual(self.status(response), 400)
        self.assertEqual(origin.received, [])

    def test_candidate_rejects_duplicate_host_before_origin_contact(self) -> None:
        source = self.prepare_source(patched=True)
        with running_server(RecordingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/package.deb"
            headers = [
                f"Host: {host}",
                f"Host: {host}",
                "Connection: close",
                "Content-Length: 0",
            ]
            with self.running_proxy(source, "duplicate-host") as proxy:
                response = self.raw_request(
                    int(proxy.server_address[1]), target, headers
                )

        self.assertEqual(self.status(response), 400)
        self.assertEqual(origin.received, [])

    def test_candidate_uses_raw_items_instead_of_collapsing_header_mapping(self) -> None:
        candidate = self.prepare_source(patched=True).read_text(encoding="utf-8")
        self.assertIn("headers.raw_items()", candidate)
        self.assertIn('headers.get_all("Connection", [])', candidate)
        self.assertIn('result.append(("Connection", "close"))', candidate)
        self.assertNotIn('dict(self.headers)', candidate)


if __name__ == "__main__":
    unittest.main()
