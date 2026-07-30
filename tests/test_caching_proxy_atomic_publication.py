from __future__ import annotations

import concurrent.futures
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
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
PATCH = (
    ROOT
    / "investigations/caching-proxy-atomic-publication"
    / "0001-publish-cache-files-atomically.patch"
)
FIRST_CHUNK = b"A" * (64 * 1024)
SECOND_CHUNK = b"B" * (64 * 1024)
FULL_BODY = FIRST_CHUNK + SECOND_CHUNK


class BlockingUpstream(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        with self.server.request_lock:
            self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(FULL_BODY)))
        self.end_headers()
        self.wfile.write(FIRST_CHUNK)
        self.wfile.flush()
        self.server.first_chunk.set()
        if not self.server.release.wait(timeout=10):
            return
        self.wfile.write(SECOND_CHUNK)
        self.wfile.flush()

    def log_message(self, _format: str, *args: object) -> None:
        return


class CachingProxyAtomicPublicationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="caching-proxy-atomic-")
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

    def test_baseline_serves_a_partially_published_cache_file(self) -> None:
        module = self.load_module(self.baseline_source)
        oldcache = self.work / "baseline-old"
        newcache = self.work / "baseline-new"
        oldcache.mkdir()
        newcache.mkdir()
        final_path = newcache / "pool/pkg.deb"

        with self.upstream_server() as upstream, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port, concurrent.futures.ThreadPoolExecutor(
            max_workers=2
        ) as executor:
            first = executor.submit(self.proxy_get, proxy_port, upstream.port)
            self.assertTrue(upstream.first_chunk.wait(timeout=5))
            self.wait_for_size(final_path, len(FIRST_CHUNK))

            second_status, second_length, second_body = self.proxy_get(
                proxy_port, upstream.port
            )
            self.assertEqual(second_status, 200)
            self.assertEqual(second_length, len(FIRST_CHUNK))
            self.assertEqual(second_body, FIRST_CHUNK)
            self.assertEqual(upstream.request_count, 1)

            upstream.release.set()
            first_status, first_length, first_body = first.result(timeout=10)

        self.assertEqual(first_status, 200)
        self.assertEqual(first_length, len(FULL_BODY))
        self.assertEqual(first_body, FULL_BODY)
        self.assertEqual(final_path.read_bytes(), FULL_BODY)

    def test_candidate_keeps_final_name_hidden_until_complete(self) -> None:
        module = self.load_module(self.candidate_source)
        oldcache = self.work / "candidate-old"
        newcache = self.work / "candidate-new"
        oldcache.mkdir()
        newcache.mkdir()
        final_path = newcache / "pool/pkg.deb"

        with self.upstream_server() as upstream, self.proxy_server(
            module, oldcache, newcache
        ) as proxy_port, concurrent.futures.ThreadPoolExecutor(
            max_workers=2
        ) as executor:
            first = executor.submit(self.proxy_get, proxy_port, upstream.port)
            self.assertTrue(upstream.first_chunk.wait(timeout=5))
            self.wait_for_temporary(newcache / "pool", ".pkg.deb.")
            self.assertFalse(final_path.exists())

            second = executor.submit(self.proxy_get, proxy_port, upstream.port)
            self.wait_for_request_count(upstream, 2)
            self.assertFalse(final_path.exists())

            upstream.release.set()
            first_result = first.result(timeout=10)
            second_result = second.result(timeout=10)

        for status, content_length, body in (first_result, second_result):
            self.assertEqual(status, 200)
            self.assertEqual(content_length, len(FULL_BODY))
            self.assertEqual(body, FULL_BODY)
        self.assertEqual(upstream.request_count, 2)
        self.assertEqual(final_path.read_bytes(), FULL_BODY)
        self.assertEqual(list(final_path.parent.glob(".pkg.deb.*")), [])

    def test_candidate_removes_temporary_file_after_writer_failure(self) -> None:
        module = self.load_module(self.candidate_source)
        destination = self.work / "failure-cache/pkg.deb"
        destination.parent.mkdir(parents=True)

        with self.assertRaisesRegex(RuntimeError, "injected writer failure"):
            with module.cache_destination(destination) as cache:
                cache.write(FIRST_CHUNK)
                raise RuntimeError("injected writer failure")

        self.assertFalse(destination.exists())
        self.assertEqual(list(destination.parent.glob(".pkg.deb.*")), [])

    def test_candidate_updates_both_cache_fill_paths_and_compiles(self) -> None:
        baseline = self.baseline_source.read_text(encoding="utf-8")
        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertEqual(baseline.count('newpath.open(mode="wb")'), 2)
        self.assertNotIn('newpath.open(mode="wb")', candidate)
        self.assertEqual(candidate.count("cache_destination(newpath)"), 2)
        self.assertIn("os.replace(temporary, path)", candidate)
        self.assertIn("temporary.unlink(missing_ok=True)", candidate)

        compiled = subprocess.run(
            ["python3", "-m", "py_compile", str(self.candidate_source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

    def load_module(self, path: pathlib.Path):
        name = f"caching_proxy_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def proxy_server(self, module, oldcache: pathlib.Path, newcache: pathlib.Path):
        module.oldcachedir = oldcache
        module.newcachedir = newcache
        module.readonly = False
        module.ProxyRequestHandler.log_message = lambda *_args: None
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), module.ProxyRequestHandler
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return RunningServer(server, thread)

    def upstream_server(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), BlockingUpstream)
        server.daemon_threads = True
        server.request_lock = threading.Lock()
        server.request_count = 0
        server.first_chunk = threading.Event()
        server.release = threading.Event()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return RunningUpstream(server, thread)

    @staticmethod
    def proxy_get(proxy_port: int, upstream_port: int) -> tuple[int, int, bytes]:
        host = f"127.0.0.1:{upstream_port}"
        target = f"http://{host}/pool/pkg.deb"
        connection = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=10)
        connection.putrequest("GET", target, skip_host=True)
        connection.putheader("Host", host)
        connection.endheaders()
        response = connection.getresponse()
        content_length = int(response.getheader("Content-Length", "-1"))
        body = response.read()
        status = response.status
        connection.close()
        return status, content_length, body

    @staticmethod
    def wait_for_size(path: pathlib.Path, minimum: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if path.exists() and path.stat().st_size >= minimum:
                return
            time.sleep(0.01)
        size = path.stat().st_size if path.exists() else None
        raise AssertionError(f"cache file did not reach {minimum} bytes: {size}")

    @staticmethod
    def wait_for_temporary(directory: pathlib.Path, prefix: str) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if directory.exists() and any(
                path.name.startswith(prefix) and path.stat().st_size >= len(FIRST_CHUNK)
                for path in directory.iterdir()
            ):
                return
            time.sleep(0.01)
        names = [path.name for path in directory.iterdir()] if directory.exists() else []
        raise AssertionError(f"temporary cache file was not populated: {names}")

    @staticmethod
    def wait_for_request_count(upstream, expected: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if upstream.request_count >= expected:
                return
            time.sleep(0.01)
        raise AssertionError(
            f"upstream saw {upstream.request_count} requests, expected {expected}"
        )


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
            raise AssertionError("proxy server thread survived shutdown")


class RunningUpstream(RunningServer):
    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    @property
    def request_count(self) -> int:
        with self.server.request_lock:
            return int(self.server.request_count)

    @property
    def first_chunk(self):
        return self.server.first_chunk

    @property
    def release(self):
        return self.server.release

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.server.release.set()
        super().__exit__(exc_type, exc, traceback)


if __name__ == "__main__":
    unittest.main()
