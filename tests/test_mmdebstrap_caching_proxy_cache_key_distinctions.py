from __future__ import annotations

import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import shutil
import socket
import subprocess
import tempfile
import threading
import types
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = ROOT / (
    "investigations/mmdebstrap-caching-proxy-containment/"
    "0001-confine-cache-paths.patch"
)
ENCODED_BODY = b"encoded-reserved-path\n"
LITERAL_BODY = b"literal-reserved-path\n"


class DistinguishingOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.server.request_count += 1
        self.server.paths.append(self.path)
        if "%3b" in self.path.lower():
            body = ENCODED_BODY
        elif "a;b.deb" in self.path:
            body = LITERAL_BODY
        else:
            body = b"ordinary\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        return


@contextlib.contextmanager
def running_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.request_count = 0
    server.paths = []
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


class CachingProxyCacheKeyDistinctionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="proxy-cache-key-")
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)
        self.baseline_source = self.work / "baseline.py"
        shutil.copy2(SOURCE, self.baseline_source)

        self.candidate_root = self.work / "candidate"
        destination = self.candidate_root / "upstream/mmdebstrap/caching_proxy.py"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=self.candidate_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.candidate_source = destination

    @staticmethod
    def load_module(path: pathlib.Path) -> types.ModuleType:
        name = f"cache_key_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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

        class QuietProxy(module.ProxyRequestHandler):
            def log_message(self, _format: str, *args: object) -> None:
                return

        with running_server(QuietProxy) as server:
            yield server, old_cache, new_cache

    @staticmethod
    def proxy_get(proxy_port: int, target: str, host: str) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=5)
        connection.putrequest("GET", target, skip_host=True)
        connection.putheader("Host", host)
        connection.putheader("Connection", "close")
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        status = response.status
        connection.close()
        return status, body

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
    def status(response: bytes) -> int:
        return int(response.split(b"\r\n", 1)[0].split(b" ", 2)[1])

    def test_baseline_collapses_encoded_and_literal_reserved_paths(self) -> None:
        with running_server(DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            encoded = f"http://{host}/debian/pool/a%3Bb.deb"
            literal = f"http://{host}/debian/pool/a;b.deb"
            with self.running_proxy(self.baseline_source, "baseline-alias") as (
                proxy,
                _old_cache,
                new_cache,
            ):
                first = self.proxy_get(int(proxy.server_address[1]), encoded, host)
                second = self.proxy_get(int(proxy.server_address[1]), literal, host)

        self.assertEqual(first, (200, ENCODED_BODY))
        self.assertEqual(second, (200, ENCODED_BODY))
        self.assertEqual(origin.request_count, 1)
        self.assertEqual(
            (new_cache / "debian/pool/a;b.deb").read_bytes(), ENCODED_BODY
        )

    def test_candidate_rejects_encoded_path_and_keeps_literal_distinct(self) -> None:
        with running_server(DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            encoded = f"http://{host}/debian/pool/a%3Bb.deb"
            literal = f"http://{host}/debian/pool/a;b.deb"
            with self.running_proxy(self.candidate_source, "candidate-alias") as (
                proxy,
                _old_cache,
                new_cache,
            ):
                rejected = self.proxy_get(int(proxy.server_address[1]), encoded, host)
                accepted = self.proxy_get(int(proxy.server_address[1]), literal, host)

        self.assertEqual(rejected[0], 400)
        self.assertEqual(accepted, (200, LITERAL_BODY))
        self.assertEqual(origin.request_count, 1)
        self.assertEqual(origin.paths, [literal])
        self.assertEqual(
            (new_cache / "debian/pool/a;b.deb").read_bytes(), LITERAL_BODY
        )

    def test_candidate_rejects_all_percent_escapes_and_literal_backslash(self) -> None:
        with running_server(DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            targets = (
                f"http://{host}/debian/pool/%FF.deb",
                f"http://{host}/debian/pool/%FE.deb",
                f"http://{host}/debian/pool/%25.deb",
                f"http://{host}/debian\\pool\\pkg.deb",
            )
            with self.running_proxy(self.candidate_source, "candidate-escapes") as (
                proxy,
                old_cache,
                new_cache,
            ):
                for target in targets:
                    with self.subTest(target=target):
                        response = self.raw_request(
                            int(proxy.server_address[1]),
                            target,
                            [f"Host: {host}", "Connection: close"],
                        )
                        self.assertEqual(self.status(response), 400)

        self.assertEqual(origin.request_count, 0)
        self.assertEqual(list(old_cache.rglob("*")), [])
        self.assertEqual(list(new_cache.rglob("*")), [])

    def test_candidate_rejects_duplicate_framing_before_origin_contact(self) -> None:
        with running_server(DistinguishingOrigin) as origin:
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/debian/pool/pkg.deb"
            cases = (
                [f"Host: {host}", f"Host: {host}", "Connection: close"],
                [
                    f"Host: {host}",
                    "Content-Length: 0",
                    "Content-Length: 0",
                    "Connection: close",
                ],
                [
                    f"Host: {host}",
                    "Content-Length: 0",
                    "Transfer-Encoding: identity",
                    "Connection: close",
                ],
            )
            with self.running_proxy(self.candidate_source, "candidate-framing") as (
                proxy,
                old_cache,
                new_cache,
            ):
                for headers in cases:
                    with self.subTest(headers=headers):
                        response = self.raw_request(
                            int(proxy.server_address[1]), target, headers
                        )
                        self.assertEqual(self.status(response), 400)

        self.assertEqual(origin.request_count, 0)
        self.assertEqual(list(old_cache.rglob("*")), [])
        self.assertEqual(list(new_cache.rglob("*")), [])

    def test_candidate_source_contract(self) -> None:
        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertIn('or "%" in raw_path', candidate)
        self.assertIn('or "\\\\" in raw_path', candidate)
        self.assertIn('self.headers.get_all("Host", [])', candidate)
        self.assertIn('self.headers.get_all("Content-Length", [])', candidate)
        self.assertIn('self.headers.get_all("Transfer-Encoding", [])', candidate)
        self.assertNotIn("urllib.parse.unquote(raw_path)", candidate)


if __name__ == "__main__":
    unittest.main()
