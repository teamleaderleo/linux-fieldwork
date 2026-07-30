from __future__ import annotations

import contextlib
import http.server
import importlib.util
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import types
import unittest


PAYLOAD = (b"complete-origin-body-" * 4096) + b"\n"
SHORT_BODY = b"short-origin-prefix\n"


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QuietHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


class CompleteOrigin(QuietHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)


class TruncatedOrigin(QuietHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(SHORT_BODY) + 1024))
        self.end_headers()
        self.wfile.write(SHORT_BODY)
        self.wfile.flush()
        self.close_connection = True


@contextlib.contextmanager
def running_server(handler: type[http.server.BaseHTTPRequestHandler]):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("server thread did not stop")


@contextlib.contextmanager
def running_proxy(
    module: types.ModuleType, old_cache: pathlib.Path, new_cache: pathlib.Path
):
    old_cache.mkdir(parents=True, exist_ok=True)
    new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = False

    class QuietProxy(module.ProxyRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

    with running_server(QuietProxy) as server:
        yield server


def raw_proxy_get(
    proxy: http.server.ThreadingHTTPServer, target: str, host: str
) -> bytes:
    with socket.create_connection(
        ("127.0.0.1", proxy.server_address[1]), timeout=5
    ) as connection:
        connection.sendall(
            (
                f"GET {target} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
        )
        chunks = []
        while True:
            chunk = connection.recv(64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def parse_response(raw: bytes) -> tuple[int, dict[str, str], bytes]:
    header_block, body = raw.split(b"\r\n\r\n", 1)
    lines = header_block.decode("iso-8859-1").split("\r\n")
    status = int(lines[0].split()[1])
    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.lower()] = value.strip()
    return status, headers, body


class MmdebstrapCachingProxyAtomicCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/caching_proxy.py"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-caching-proxy-atomic-cache/"
            "0001-publish-cache-files-atomically.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="proxy-atomic-candidate-")
        cls.candidate_root = pathlib.Path(cls.work.name) / "candidate"
        cls.candidate_source = (
            cls.candidate_root / "upstream/mmdebstrap/caching_proxy.py"
        )
        cls.candidate_source.parent.mkdir(parents=True)
        shutil.copy2(cls.source, cls.candidate_source)
        applied = subprocess.run(
            [
                "patch",
                "--batch",
                "--forward",
                "-p1",
                "-i",
                str(cls.patch),
            ],
            cwd=cls.candidate_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if applied.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(applied.stdout + applied.stderr)
        compiled = subprocess.run(
            [sys.executable, "-m", "py_compile", str(cls.candidate_source)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if compiled.returncode != 0:
            cls.work.cleanup()
            raise AssertionError(compiled.stdout + compiled.stderr)
        cls.baseline = load_module(cls.source, "lf_proxy_atomic_baseline")
        cls.candidate = load_module(cls.candidate_source, "lf_proxy_atomic_candidate")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def test_baseline_promotes_and_reuses_truncated_origin_body(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-baseline-short-") as tmp:
            root = pathlib.Path(tmp)
            old_cache = root / "old"
            new_cache = root / "new"
            with running_server(TruncatedOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/debian/pool/truncated.deb"
                with running_proxy(self.baseline, old_cache, new_cache) as proxy:
                    first = raw_proxy_get(proxy, target, host)
            first_status, first_headers, first_body = parse_response(first)
            self.assertEqual(first_status, 200)
            self.assertEqual(
                int(first_headers["content-length"]), len(SHORT_BODY) + 1024
            )
            self.assertEqual(first_body, SHORT_BODY)

            cached = new_cache / "debian/pool/truncated.deb"
            self.assertEqual(cached.read_bytes(), SHORT_BODY)
            with running_proxy(self.baseline, old_cache, new_cache) as proxy:
                second = raw_proxy_get(proxy, target, host)
            status, headers, body = parse_response(second)
            self.assertEqual(status, 200)
            self.assertEqual(int(headers["content-length"]), len(SHORT_BODY))
            self.assertEqual(body, SHORT_BODY)

    def test_candidate_rejects_short_body_without_publishing_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-candidate-short-") as tmp:
            root = pathlib.Path(tmp)
            old_cache = root / "old"
            new_cache = root / "new"
            with running_server(TruncatedOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/debian/pool/truncated.deb"
                with running_proxy(self.candidate, old_cache, new_cache) as proxy:
                    raw = raw_proxy_get(proxy, target, host)
            status, headers, body = parse_response(raw)
            self.assertEqual(status, 200)
            self.assertEqual(
                int(headers["content-length"]), len(SHORT_BODY) + 1024
            )
            self.assertEqual(body, SHORT_BODY)
            cached = new_cache / "debian/pool/truncated.deb"
            self.assertFalse(cached.exists())
            self.assertEqual(list(cached.parent.glob(".truncated.deb.*")), [])

    def test_complete_body_is_atomically_cached_and_reused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-candidate-complete-") as tmp:
            root = pathlib.Path(tmp)
            old_cache = root / "old"
            new_cache = root / "new"
            with running_server(CompleteOrigin) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/debian/pool/complete.deb"
                with running_proxy(self.candidate, old_cache, new_cache) as proxy:
                    first = raw_proxy_get(proxy, target, host)
            status, headers, body = parse_response(first)
            self.assertEqual(status, 200)
            self.assertEqual(int(headers["content-length"]), len(PAYLOAD))
            self.assertEqual(body, PAYLOAD)

            cached = new_cache / "debian/pool/complete.deb"
            self.assertEqual(cached.read_bytes(), PAYLOAD)
            self.assertEqual(list(cached.parent.glob(".complete.deb.*")), [])
            with running_proxy(self.candidate, old_cache, new_cache) as proxy:
                second = raw_proxy_get(proxy, target, host)
            status, headers, body = parse_response(second)
            self.assertEqual(status, 200)
            self.assertEqual(int(headers["content-length"]), len(PAYLOAD))
            self.assertEqual(body, PAYLOAD)

    def test_atomic_writer_removes_interrupted_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-writer-interrupt-") as tmp:
            root = pathlib.Path(tmp)
            final = root / "object.deb"
            with self.assertRaisesRegex(RuntimeError, "interrupt"):
                with self.candidate.atomic_cache_writer(final) as stream:
                    stream.write(b"partial")
                    raise RuntimeError("interrupt")
            self.assertFalse(final.exists())
            self.assertEqual(list(root.glob(".object.deb.*")), [])

    def test_old_cache_copy_uses_atomic_promotion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-old-cache-") as tmp:
            root = pathlib.Path(tmp)
            old_cache = root / "old"
            new_cache = root / "new"
            source = old_cache / "debian/pool/from-old.deb"
            source.parent.mkdir(parents=True)
            source.write_bytes(PAYLOAD)
            host = "example.invalid"
            target = f"http://{host}/debian/pool/from-old.deb"
            with running_proxy(self.candidate, old_cache, new_cache) as proxy:
                raw = raw_proxy_get(proxy, target, host)
            status, headers, body = parse_response(raw)
            self.assertEqual(status, 200)
            self.assertEqual(int(headers["content-length"]), len(PAYLOAD))
            self.assertEqual(body, PAYLOAD)
            copied = new_cache / "debian/pool/from-old.deb"
            self.assertEqual(copied.read_bytes(), PAYLOAD)
            self.assertEqual(list(copied.parent.glob(".from-old.deb.*")), [])

    def test_candidate_source_uses_atomic_writer_in_both_paths(self) -> None:
        source = self.candidate_source.read_text(encoding="utf-8")
        self.assertEqual(source.count("atomic_cache_writer(newpath)"), 2)
        self.assertIn("received != expected_size", source)
        self.assertIn("self.close_connection = True", source)


if __name__ == "__main__":
    unittest.main()
