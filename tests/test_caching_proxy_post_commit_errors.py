from __future__ import annotations

import contextlib
import http.client
import http.server
import importlib.util
import io
import os
import pathlib
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
import uuid
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/mmdebstrap/caching_proxy.py"
ATOMIC_PATCH = ROOT / (
    "investigations/caching-proxy-atomic-publication/"
    "0001-publish-cache-files-atomically.patch"
)
ERROR_PATCH = ROOT / (
    "investigations/caching-proxy-post-commit-errors/"
    "0001-close-after-committed-response-errors.patch"
)
STATUS_RE = re.compile(br"HTTP/\d\.\d (\d{3})")
PREFIX = b"BODY-PREFIX"


class ScriptedResponse:
    status = 200
    reason = "OK"

    def __init__(self, reads: list[bytes | BaseException]) -> None:
        self.reads = list(reads)

    def getheaders(self) -> list[tuple[str, str]]:
        return [("Content-Type", "application/octet-stream")]

    def read(self, _size: int) -> bytes:
        if not self.reads:
            return b""
        item = self.reads.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class ScriptedConnection:
    def __init__(
        self,
        response: ScriptedResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.response = response
        self.error = error

    def request(self, *_args, **_kwargs) -> None:
        return

    def getresponse(self) -> ScriptedResponse:
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("scripted response is missing")
        return self.response


class ConnectionFactory:
    def __init__(
        self,
        response: ScriptedResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.response = response
        self.error = error

    def __call__(self, *_args, **_kwargs) -> ScriptedConnection:
        return ScriptedConnection(self.response, self.error)


class FailingBodyWriter:
    """Allow the status and header writes, then emulate a client disconnect."""

    def __init__(self, wrapped) -> None:
        self.wrapped = wrapped
        self.calls = 0

    def write(self, data: bytes) -> int:
        self.calls += 1
        if self.calls >= 3:
            raise BrokenPipeError("injected downstream disconnect")
        return self.wrapped.write(data)

    def flush(self) -> None:
        self.wrapped.flush()

    def __getattr__(self, name: str):
        return getattr(self.wrapped, name)


class CachingProxyPostCommitErrorsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="caching-proxy-post-commit-"
        )
        self.addCleanup(self.temporary.cleanup)
        self.work = pathlib.Path(self.temporary.name)

        self.atomic_tree = self.work / "atomic"
        self.atomic_source = self.prepare_source(
            self.atomic_tree, (ATOMIC_PATCH,)
        )
        self.candidate_tree = self.work / "candidate"
        self.candidate_source = self.prepare_source(
            self.candidate_tree, (ATOMIC_PATCH, ERROR_PATCH)
        )

    def prepare_source(
        self, tree: pathlib.Path, patches: tuple[pathlib.Path, ...]
    ) -> pathlib.Path:
        destination = tree / "upstream/mmdebstrap/caching_proxy.py"
        destination.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, destination)
        for patch in patches:
            applied = subprocess.run(
                ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                cwd=tree,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                applied.returncode,
                0,
                f"{patch.name}:\n{applied.stdout}{applied.stderr}",
            )
        return destination

    @staticmethod
    def load_module(path: pathlib.Path):
        name = f"caching_proxy_post_commit_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise AssertionError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @contextlib.contextmanager
    def running_proxy(self, module, *, disconnect_after_headers: bool = False):
        oldcache = self.work / uuid.uuid4().hex / "old"
        newcache = oldcache.parent / "new"
        oldcache.mkdir(parents=True)
        newcache.mkdir()
        module.oldcachedir = oldcache
        module.newcachedir = newcache
        module.readonly = False

        base = module.ProxyRequestHandler

        class QuietProxy(base):
            def log_message(self, _format: str, *args: object) -> None:
                return

            def setup(self) -> None:
                super().setup()
                if disconnect_after_headers:
                    self.wfile = FailingBodyWriter(self.wfile)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietProxy)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield int(server.server_address[1]), newcache
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            if thread.is_alive():
                raise AssertionError("proxy thread survived shutdown")

    @staticmethod
    def raw_get(port: int) -> bytes:
        request = (
            "GET http://origin.invalid/pool/pkg.deb HTTP/1.1\r\n"
            "Host: origin.invalid\r\n"
            "Connection: close\r\n"
            "Content-Length: 0\r\n"
            "\r\n"
        ).encode("ascii")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
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
    def statuses(response: bytes) -> list[int]:
        return [int(value) for value in STATUS_RE.findall(response)]

    @staticmethod
    def cache_entries(root: pathlib.Path) -> list[pathlib.Path]:
        return [path for path in root.rglob("*") if path.is_file()]

    def execute(
        self,
        source: pathlib.Path,
        factory: ConnectionFactory,
        *,
        disconnect_after_headers: bool = False,
        fdopen=None,
    ) -> tuple[bytes, str, pathlib.Path]:
        module = self.load_module(source)
        stderr = io.StringIO()
        original_connection = module.http.client.HTTPConnection
        module.http.client.HTTPConnection = factory
        try:
            patcher = (
                mock.patch.object(module.os, "fdopen", fdopen)
                if fdopen is not None
                else contextlib.nullcontext()
            )
            with patcher, contextlib.redirect_stderr(stderr), self.running_proxy(
                module, disconnect_after_headers=disconnect_after_headers
            ) as (port, newcache):
                response = self.raw_get(port)
        finally:
            module.http.client.HTTPConnection = original_connection
        return response, stderr.getvalue(), newcache

    def test_atomic_only_baseline_appends_second_response_after_body_error(self) -> None:
        response, _stderr, cache = self.execute(
            self.atomic_source,
            ConnectionFactory(
                ScriptedResponse([PREFIX, RuntimeError("injected origin read failure")])
            ),
        )

        self.assertEqual(self.statuses(response), [200, 502])
        self.assertIn(PREFIX, response)
        self.assertIn(b"Bad Gateway", response)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_sends_normal_502_before_response_commit(self) -> None:
        response, stderr, cache = self.execute(
            self.candidate_source,
            ConnectionFactory(error=ConnectionError("injected pre-commit failure")),
        )

        self.assertEqual(self.statuses(response), [502])
        self.assertIn(b"Bad Gateway", response)
        self.assertIn("injected pre-commit failure", stderr)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_closes_after_headers_without_appending_502(self) -> None:
        response, stderr, cache = self.execute(
            self.candidate_source,
            ConnectionFactory(
                ScriptedResponse([RuntimeError("injected post-header failure")])
            ),
        )

        self.assertEqual(self.statuses(response), [200])
        self.assertNotIn(b"Bad Gateway", response)
        self.assertNotIn(b"HTTP/1.0 502", response)
        self.assertIn("injected post-header failure", stderr)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_closes_after_body_prefix_without_appending_502(self) -> None:
        response, stderr, cache = self.execute(
            self.candidate_source,
            ConnectionFactory(
                ScriptedResponse([PREFIX, RuntimeError("injected prefix failure")])
            ),
        )

        self.assertEqual(self.statuses(response), [200])
        self.assertIn(PREFIX, response)
        self.assertNotIn(b"Bad Gateway", response)
        self.assertIn("injected prefix failure", stderr)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_closes_on_cache_writer_open_failure_and_cleans_temporary(self) -> None:
        def failing_fdopen(descriptor: int, *args, **kwargs):
            os.close(descriptor)
            raise OSError("injected cache writer failure")

        response, stderr, cache = self.execute(
            self.candidate_source,
            ConnectionFactory(ScriptedResponse([PREFIX, b""])),
            fdopen=failing_fdopen,
        )

        self.assertEqual(self.statuses(response), [200])
        self.assertNotIn(b"Bad Gateway", response)
        self.assertIn("injected cache writer failure", stderr)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_handles_downstream_disconnect_without_cache_publication(self) -> None:
        response, stderr, cache = self.execute(
            self.candidate_source,
            ConnectionFactory(ScriptedResponse([PREFIX, b""])),
            disconnect_after_headers=True,
        )

        self.assertEqual(self.statuses(response), [200])
        self.assertNotIn(b"Bad Gateway", response)
        self.assertIn("injected downstream disconnect", stderr)
        self.assertEqual(self.cache_entries(cache), [])

    def test_candidate_source_contract_and_compilation(self) -> None:
        atomic = self.atomic_source.read_text(encoding="utf-8")
        candidate = self.candidate_source.read_text(encoding="utf-8")
        self.assertNotIn("response_started = False", atomic)
        self.assertIn("response_started = False", candidate)
        self.assertIn("response_started = True", candidate)
        self.assertIn("if response_started:", candidate)
        self.assertIn("self.close_connection = True", candidate)
        self.assertIn('print(f"proxy error: {e!r}"', candidate)

        compiled = subprocess.run(
            ["python3", "-m", "py_compile", str(self.candidate_source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)


if __name__ == "__main__":
    unittest.main()
