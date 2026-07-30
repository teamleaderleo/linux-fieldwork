from __future__ import annotations

import contextlib
import http.client
import http.server
import importlib.util
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
import urllib.parse


PAYLOAD = b"linux-fieldwork-proxy-payload\n"
SECRET = b"linux-fieldwork-outside-secret\n"


def load_module(path: pathlib.Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OriginHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextlib.contextmanager
def running_server(handler: type[http.server.BaseHTTPRequestHandler]):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
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
            raise AssertionError("HTTP server thread did not stop")


@contextlib.contextmanager
def running_proxy(
    module: types.ModuleType,
    old_cache: pathlib.Path,
    new_cache: pathlib.Path,
    *,
    readonly: bool = False,
):
    old_cache.mkdir(parents=True, exist_ok=True)
    new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = readonly

    class QuietProxy(module.ProxyRequestHandler):
        def log_message(self, _format: str, *_args: object) -> None:
            return

    with running_server(QuietProxy) as server:
        yield server


def proxy_get(
    proxy: http.server.ThreadingHTTPServer, request_target: str, host: str
) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection(
        "127.0.0.1", proxy.server_address[1], timeout=5
    )
    try:
        connection.request(
            "GET",
            request_target,
            headers={"Host": host, "Connection": "close"},
        )
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


class MmdebstrapCachingProxyContainmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.source = cls.repo / "upstream/mmdebstrap/caching_proxy.py"
        cls.patch = cls.repo / (
            "investigations/mmdebstrap-caching-proxy-containment/"
            "0001-confine-cache-paths.patch"
        )
        cls.work = tempfile.TemporaryDirectory(prefix="mmdebstrap-proxy-containment-")
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
        cls.baseline = load_module(cls.source, "lf_proxy_baseline")
        cls.candidate = load_module(cls.candidate_source, "lf_proxy_candidate")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.work.cleanup()

    def test_candidate_preserves_legitimate_proxy_caching(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-legitimate-") as tmp:
            root = pathlib.Path(tmp)
            with running_server(OriginHandler) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/debian/pool/main/p/package.deb"
                for name, module in (
                    ("baseline", self.baseline),
                    ("candidate", self.candidate),
                ):
                    old_cache = root / name / "old"
                    new_cache = root / name / "new"
                    with running_proxy(module, old_cache, new_cache) as proxy:
                        status, body = proxy_get(proxy, target, host)
                    self.assertEqual(status, 200)
                    self.assertEqual(body, PAYLOAD)
                    cached = new_cache / "debian/pool/main/p/package.deb"
                    self.assertEqual(cached.read_bytes(), PAYLOAD)

    def test_candidate_accepts_case_insensitive_hostname_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-host-case-") as tmp:
            root = pathlib.Path(tmp)
            with running_server(OriginHandler) as origin:
                port = origin.server_address[1]
                host = f"LOCALHOST:{port}"
                target = f"http://localhost:{port}/debian/pool/package.deb"
                new_cache = root / "new"
                with running_proxy(
                    self.candidate, root / "old", new_cache
                ) as proxy:
                    status, body = proxy_get(proxy, target, host)
                self.assertEqual(status, 200)
                self.assertEqual(body, PAYLOAD)
                self.assertEqual(origin.request_count, 1)
                self.assertEqual(
                    (new_cache / "debian/pool/package.deb").read_bytes(), PAYLOAD
                )

    def test_dot_empty_and_trailing_components_are_rejected_before_origin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-alias-components-") as tmp:
            root = pathlib.Path(tmp)
            old_cache = root / "old"
            new_cache = root / "new"
            with running_server(OriginHandler) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                targets = (
                    f"http://{host}/debian/pool/./package.deb",
                    f"http://{host}/debian/pool/%2e/package.deb",
                    f"http://{host}/debian/pool/package.deb/",
                    f"http://{host}/debian//pool/package.deb",
                )
                with running_proxy(
                    self.candidate, old_cache, new_cache
                ) as proxy:
                    for target in targets:
                        with self.subTest(target=target):
                            status, _body = proxy_get(proxy, target, host)
                            self.assertEqual(status, 400)

                self.assertEqual(origin.request_count, 0)
                self.assertEqual(list(old_cache.rglob("*")), [])
                self.assertEqual(list(new_cache.rglob("*")), [])

    def test_absolute_request_target_cannot_write_outside_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-absolute-write-") as tmp:
            root = pathlib.Path(tmp)
            outside = root / "outside" / "owned"
            with running_server(OriginHandler) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                encoded = urllib.parse.quote(outside.as_posix(), safe="/")
                target = f"http://{host}/{encoded}"

                with running_proxy(
                    self.baseline, root / "baseline-old", root / "baseline-new"
                ) as proxy:
                    status, body = proxy_get(proxy, target, host)
                self.assertEqual(status, 200)
                self.assertEqual(body, PAYLOAD)
                self.assertEqual(outside.read_bytes(), PAYLOAD)

                outside.unlink()
                with running_proxy(
                    self.candidate, root / "candidate-old", root / "candidate-new"
                ) as proxy:
                    status, _body = proxy_get(proxy, target, host)
                self.assertEqual(status, 400)
                self.assertFalse(outside.exists())

    def test_percent_encoded_dot_segments_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-dot-segment-") as tmp:
            root = pathlib.Path(tmp)
            outside = root / "baseline" / "escaped"
            with running_server(OriginHandler) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/%2e%2e/escaped"

                with running_proxy(
                    self.baseline,
                    root / "baseline" / "old",
                    root / "baseline" / "new",
                ) as proxy:
                    status, _body = proxy_get(proxy, target, host)
                self.assertEqual(status, 200)
                self.assertEqual(outside.read_bytes(), PAYLOAD)

                candidate_outside = root / "candidate" / "escaped"
                with running_proxy(
                    self.candidate,
                    root / "candidate" / "old",
                    root / "candidate" / "new",
                ) as proxy:
                    status, _body = proxy_get(proxy, target, host)
                self.assertEqual(status, 400)
                self.assertFalse(candidate_outside.exists())

    def test_existing_absolute_file_cannot_be_read_through_proxy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-absolute-read-") as tmp:
            root = pathlib.Path(tmp)
            secret = root / "outside-secret.txt"
            secret.write_bytes(SECRET)
            host = "example.invalid"
            encoded = urllib.parse.quote(secret.as_posix(), safe="/")
            target = f"http://{host}/{encoded}"

            with running_proxy(
                self.baseline, root / "baseline-old", root / "baseline-new"
            ) as proxy:
                status, body = proxy_get(proxy, target, host)
            self.assertEqual(status, 200)
            self.assertEqual(body, SECRET)

            with running_proxy(
                self.candidate, root / "candidate-old", root / "candidate-new"
            ) as proxy:
                status, body = proxy_get(proxy, target, host)
            self.assertEqual(status, 400)
            self.assertNotEqual(body, SECRET)
            self.assertEqual(secret.read_bytes(), SECRET)

    def test_symlinked_cache_parent_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="proxy-symlink-") as tmp:
            root = pathlib.Path(tmp)
            outside = root / "outside"
            outside.mkdir()
            with running_server(OriginHandler) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/link/owned"

                baseline_new = root / "baseline-new"
                baseline_new.mkdir()
                (baseline_new / "link").symlink_to(outside, target_is_directory=True)
                with running_proxy(
                    self.baseline, root / "baseline-old", baseline_new
                ) as proxy:
                    status, _body = proxy_get(proxy, target, host)
                self.assertEqual(status, 200)
                self.assertEqual((outside / "owned").read_bytes(), PAYLOAD)

                (outside / "owned").unlink()
                candidate_new = root / "candidate-new"
                candidate_new.mkdir()
                (candidate_new / "link").symlink_to(outside, target_is_directory=True)
                with running_proxy(
                    self.candidate, root / "candidate-old", candidate_new
                ) as proxy:
                    status, _body = proxy_get(proxy, target, host)
                self.assertEqual(status, 400)
                self.assertFalse((outside / "owned").exists())

    def test_candidate_main_binds_loopback_only(self) -> None:
        baseline = self.source.read_text(encoding="utf-8")
        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertIn('server_address=("", 8080)', baseline)
        self.assertIn('server_address=("127.0.0.1", 8080)', candidate)
        self.assertIn('components = raw_path.split("/")', candidate)
        self.assertIn('part in ("", ".", "..")', candidate)
        self.assertIn("parsed.hostname.lower()", candidate)
        self.assertIn("candidate.is_relative_to(root)", candidate)


if __name__ == "__main__":
    unittest.main()
