from __future__ import annotations

import http.client
import http.server
import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.parse
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = (
    ROOT
    / "investigations/caching-proxy-cache-containment"
    / "0001-contain-cache-paths.patch"
)


class QuietUpstream(http.server.BaseHTTPRequestHandler):
    body = b"ATTACKER-CONTROLLED"
    requests = 0

    def do_GET(self) -> None:
        type(self).requests += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(type(self).body)))
        self.end_headers()
        self.wfile.write(type(self).body)

    def log_message(self, _format: str, *args: object) -> None:
        return


class CachingProxyCacheContainmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="caching-proxy-containment-")
        self.addCleanup(self.tempdir.cleanup)
        self.work = pathlib.Path(self.tempdir.name)
        self.baseline_source = self.work / "baseline-caching-proxy.py"
        shutil.copy2(SOURCE, self.baseline_source)

        self.tree = self.work / "candidate-tree"
        candidate_dir = self.tree / "upstream/mmdebstrap"
        candidate_dir.mkdir(parents=True)
        self.candidate_source = candidate_dir / "caching_proxy.py"
        shutil.copy2(SOURCE, self.candidate_source)
        applied = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=self.tree,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)

    def test_baseline_reads_and_writes_outside_the_cache(self) -> None:
        outside_read = self.work / "outside-read"
        outside_read.write_bytes(b"TOP-SECRET")

        module = self.load_module(self.baseline_source)
        oldcache = self.work / "baseline-old"
        newcache = self.work / "baseline-new"
        oldcache.mkdir()
        newcache.mkdir()

        with self.proxy_server(module, oldcache, newcache) as proxy_port:
            suffix = urllib.parse.quote(str(outside_read), safe="")
            status, body = self.proxy_get(proxy_port, "example.invalid", suffix)
            self.assertEqual(status, 200)
            self.assertEqual(body, b"TOP-SECRET")

            outside_write = self.work / "outside-write"
            with self.upstream_server() as upstream_port:
                host = f"127.0.0.1:{upstream_port}"
                suffix = urllib.parse.quote(str(outside_write), safe="")
                status, body = self.proxy_get(proxy_port, host, suffix)
                self.assertEqual(status, 200)
                self.assertEqual(body, QuietUpstream.body)
                self.wait_for_bytes(outside_write, QuietUpstream.body)

    def test_candidate_rejects_absolute_parent_and_symlink_escapes(self) -> None:
        outside_dir = self.work / "outside"
        outside_dir.mkdir()
        outside_secret = outside_dir / "secret"
        outside_secret.write_bytes(b"OUTSIDE")

        module = self.load_module(self.candidate_source)
        oldcache = self.work / "candidate-old"
        newcache = self.work / "candidate-new"
        oldcache.mkdir()
        newcache.mkdir()
        (newcache / "link").symlink_to(outside_dir, target_is_directory=True)

        with self.proxy_server(module, oldcache, newcache) as proxy_port:
            absolute = urllib.parse.quote(str(outside_secret), safe="")
            status, body = self.proxy_get(proxy_port, "example.invalid", absolute)
            self.assertEqual(status, 400)
            self.assertNotIn(b"OUTSIDE", body)

            status, _ = self.proxy_get(proxy_port, "example.invalid", "../outside/secret")
            self.assertEqual(status, 400)

            encoded_parent = urllib.parse.quote("../outside/secret", safe="")
            status, _ = self.proxy_get(proxy_port, "example.invalid", encoded_parent)
            self.assertEqual(status, 400)

            status, body = self.proxy_get(proxy_port, "example.invalid", "link/secret")
            self.assertEqual(status, 400)
            self.assertNotIn(b"OUTSIDE", body)

    def test_candidate_rejects_outside_write_before_contacting_upstream(self) -> None:
        module = self.load_module(self.candidate_source)
        oldcache = self.work / "write-old"
        newcache = self.work / "write-new"
        oldcache.mkdir()
        newcache.mkdir()
        outside_write = self.work / "candidate-outside-write"

        QuietUpstream.requests = 0
        with self.upstream_server() as upstream_port, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port:
            host = f"127.0.0.1:{upstream_port}"
            suffix = urllib.parse.quote(str(outside_write), safe="")
            status, _ = self.proxy_get(proxy_port, host, suffix)
            self.assertEqual(status, 400)

        self.assertEqual(QuietUpstream.requests, 0)
        self.assertFalse(outside_write.exists())

    def test_candidate_preserves_valid_cache_hits_and_readonly_rejection(self) -> None:
        module = self.load_module(self.candidate_source)
        oldcache = self.work / "valid-old"
        newcache = self.work / "valid-new"
        oldcache.mkdir()
        cached = newcache / "debian/pool/main/p/pkg.deb"
        cached.parent.mkdir(parents=True)
        cached.write_bytes(b"VALID-DEB")

        with self.proxy_server(module, oldcache, newcache) as proxy_port:
            status, body = self.proxy_get(
                proxy_port, "deb.debian.org", "debian/pool/main/p/pkg.deb"
            )
            self.assertEqual(status, 200)
            self.assertEqual(body, b"VALID-DEB")

        outside = self.work / "readonly-outside"
        outside.write_bytes(b"READONLY-SECRET")
        module = self.load_module(self.candidate_source)
        module.readonly = True
        with self.proxy_server(
            module, oldcache, newcache, preserve_readonly=True
        ) as proxy_port:
            suffix = urllib.parse.quote(str(outside), safe="")
            status, body = self.proxy_get(proxy_port, "example.invalid", suffix)
            self.assertEqual(status, 400)
            self.assertNotIn(b"READONLY-SECRET", body)

    def test_candidate_compiles_and_binds_main_to_loopback(self) -> None:
        compiled = subprocess.run(
            ["python3", "-m", "py_compile", str(self.candidate_source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertIn('server_address=("127.0.0.1", 8080)', candidate)
        self.assertNotIn('server_address=("", 8080)', candidate)
        self.assertIn("candidate.is_relative_to(root)", candidate)
        self.assertIn('self.send_error(400, "invalid cache path")', candidate)

    def load_module(self, path: pathlib.Path):
        name = f"caching_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def proxy_server(
        self,
        module,
        oldcache: pathlib.Path,
        newcache: pathlib.Path,
        preserve_readonly: bool = False,
    ):
        if not preserve_readonly:
            module.readonly = False
        module.oldcachedir = oldcache
        module.newcachedir = newcache
        module.ProxyRequestHandler.log_message = lambda *_args: None
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), module.ProxyRequestHandler
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        return RunningServer(server, thread)

    def upstream_server(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietUpstream)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        return RunningServer(server, thread)

    @staticmethod
    def proxy_get(proxy_port: int, host: str, suffix: str) -> tuple[int, bytes]:
        target = f"http://{host}/{suffix}"
        connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=5)
        connection.putrequest("GET", target, skip_host=True)
        connection.putheader("Host", host)
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, body

    @staticmethod
    def wait_for_bytes(path: pathlib.Path, expected: bytes) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if path.exists() and path.read_bytes() == expected:
                return
            time.sleep(0.01)
        actual = path.read_bytes() if path.exists() else None
        raise AssertionError(f"outside write mismatch: {actual!r}")


class RunningServer:
    def __init__(self, server: http.server.ThreadingHTTPServer, thread: threading.Thread):
        self.server = server
        self.thread = thread

    def __enter__(self) -> int:
        return int(self.server.server_address[1])

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise AssertionError("server thread survived shutdown")


if __name__ == "__main__":
    unittest.main()
