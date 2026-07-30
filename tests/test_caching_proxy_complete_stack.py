from __future__ import annotations

import concurrent.futures
import contextlib
import email.message
import http.client
import http.server
import importlib.util
import io
import json
import os
import pathlib
import re
import socket
import socketserver
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
from unittest import mock


STATUS_RE = re.compile(br"HTTP/\d\.\d (\d{3})")
PAYLOAD = b"A" * (128 * 1024)
PREFIX = b"BODY-PREFIX"
CHUNKED = b"chunk-one-chunk-two"


def load_module(path: pathlib.Path, prefix: str = "lf_complete") -> types.ModuleType:
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def running_http_server(handler):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    server.request_count = 0
    server.lock = threading.Lock()
    server.atomic_started = threading.Event()
    server.atomic_release = threading.Event()
    server.captured_headers = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.atomic_release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("HTTP server did not stop")


@contextlib.contextmanager
def running_raw_server(responses):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            while True:
                line = self.rfile.readline()
                if line in (b"", b"\r\n", b"\n"):
                    break
            with self.server.lock:
                index = self.server.request_count
                self.server.request_count += 1
            response = responses[min(index, len(responses) - 1)]
            self.wfile.write(response)
            self.wfile.flush()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    server.request_count = 0
    server.lock = threading.Lock()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise AssertionError("raw HTTP server did not stop")


@contextlib.contextmanager
def running_proxy(
    module,
    old_cache: pathlib.Path,
    new_cache: pathlib.Path,
    *,
    disconnect=False,
):
    old_cache.mkdir(parents=True, exist_ok=True)
    new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = old_cache
    module.newcachedir = new_cache
    module.readonly = False

    class FailingBodyWriter:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.calls = 0

        def write(self, data):
            self.calls += 1
            if self.calls >= 3:
                raise BrokenPipeError("injected downstream disconnect")
            return self.wrapped.write(data)

        def flush(self):
            return self.wrapped.flush()

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

    class QuietProxy(module.ProxyRequestHandler):
        def log_message(self, _format, *_args):
            return

        def setup(self):
            super().setup()
            if disconnect:
                self.wfile = FailingBodyWriter(self.wfile)

    with running_http_server(QuietProxy) as server:
        yield server


def raw_request(proxy, request: bytes) -> bytes:
    with socket.create_connection(
        ("127.0.0.1", proxy.server_address[1]), timeout=5
    ) as client:
        client.settimeout(10)
        client.sendall(request)
        result = bytearray()
        while True:
            block = client.recv(65536)
            if not block:
                break
            result.extend(block)
    return bytes(result)


def request_bytes(method: str, target: str, headers: list[tuple[str, str]]) -> bytes:
    lines = [f"{method} {target} HTTP/1.1"]
    lines.extend(f"{name}: {value}" for name, value in headers)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")


def statuses(response: bytes) -> list[int]:
    return [int(value) for value in STATUS_RE.findall(response)]


def body_bytes(response: bytes) -> bytes:
    return response.split(b"\r\n\r\n", 1)[1]


def headers_bytes(response: bytes) -> bytes:
    return response.split(b"\r\n\r\n", 1)[0].lower()


def wait_for_no_temporaries(directory: pathlib.Path) -> None:
    deadline = time.monotonic() + 5
    temporary = []
    while time.monotonic() < deadline:
        if not directory.exists():
            return
        temporary = [path for path in directory.iterdir() if path.name.startswith(".")]
        if not temporary:
            return
        time.sleep(0.02)
    raise AssertionError(f"temporary cache files survived: {temporary}")


def wait_for_cache(path: pathlib.Path, size: int) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            if path.stat().st_size == size:
                return
        except FileNotFoundError:
            pass
        time.sleep(0.02)
    raise AssertionError(f"cache publication did not complete: {path}")


class FixedOrigin(http.server.BaseHTTPRequestHandler):
    body = PAYLOAD
    reason = "Mirror Success"

    def do_GET(self):
        with self.server.lock:
            self.server.request_count += 1
            self.server.captured_headers.append(list(self.headers.raw_items()))
        self.send_response(200, self.reason)
        self.send_header("Content-Length", str(len(self.body)))
        self.send_header("X-End-To-End", "preserved")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, _format, *_args):
        return


class AtomicOrigin(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with self.server.lock:
            self.server.request_count += 1
        self.send_response(200)
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.send_header("Connection", "close")
        self.end_headers()
        half = len(PAYLOAD) // 2
        self.wfile.write(PAYLOAD[:half])
        self.wfile.flush()
        self.server.atomic_started.set()
        if self.server.atomic_release.wait(timeout=10):
            self.wfile.write(PAYLOAD[half:])
            self.wfile.flush()

    def log_message(self, _format, *_args):
        return


class ScriptedResponse:
    status = 200
    reason = "OK"
    chunked = False

    def __init__(self, reads):
        self.reads = list(reads)
        self.headers = email.message.Message()
        self.headers["Content-Type"] = "application/octet-stream"

    def getheaders(self):
        return list(self.headers.items())

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read(self, _size):
        if not self.reads:
            return b""
        item = self.reads.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class ScriptedConnection:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def putrequest(self, *_args, **_kwargs):
        return None

    def putheader(self, *_args, **_kwargs):
        return None

    def endheaders(self):
        return None

    def close(self):
        return None

    def getresponse(self):
        if self.error is not None:
            raise self.error
        if self.response is None:
            raise AssertionError("missing scripted response")
        return self.response


class ConnectionFactory:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def __call__(self, *_args, **_kwargs):
        return ScriptedConnection(self.response, self.error)


class CachingProxyCompleteStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = pathlib.Path(__file__).resolve().parents[1]
        cls.composer_path = cls.repo / (
            "investigations/caching-proxy-complete-stack/compose.py"
        )
        cls.runner = cls.repo / (
            "investigations/caching-proxy-complete-stack/run_case.py"
        )
        cls.composer = load_module(cls.composer_path, "lf_complete_composer")
        cls.work = tempfile.TemporaryDirectory(prefix="complete-proxy-stack-")
        cls.candidate = cls.composer.compose(
            cls.repo, pathlib.Path(cls.work.name) / "candidate"
        )
        cls.module = load_module(cls.candidate)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def test_manifest_source_contract_and_compilation(self):
        self.assertEqual(len(self.composer.REQUIRED_REPAIRS), 8)
        for relative in self.composer.REQUIRED_REPAIRS:
            self.assertTrue((self.repo / relative).is_file(), relative)
        source = self.candidate.read_text(encoding="utf-8")
        for marker in (
            "def request_context(",
            "def origin_request_headers(",
            "def validate_transfer_encoding(",
            "def downstream_headers(",
            "os.O_WRONLY | os.O_CREAT | os.O_EXCL",
            "if res.status != 200:",
            "response_started = False",
            "if response_started:",
            "received != expected_length",
            'server_address=("127.0.0.1", 8080)',
        ):
            self.assertIn(marker, source)
        self.assertNotIn("assert ", source)
        for optimize in ((), ("-O",)):
            completed = subprocess.run(
                [sys.executable, *optimize, "-m", "py_compile", str(self.candidate)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )

    def test_request_boundary_rejects_before_origin_or_cache(self):
        with running_http_server(FixedOrigin) as origin, tempfile.TemporaryDirectory(
            prefix="complete-request-"
        ) as tmp:
            root = pathlib.Path(tmp)
            host = f"127.0.0.1:{origin.server_address[1]}"
            valid = f"http://{host}/pool/object.deb"
            cases = (
                ("POST", valid, [("Host", host)], 405),
                ("GET", valid, [("Host", "example.invalid")], 400),
                ("GET", f"http://user@{host}/pool/object.deb", [("Host", host)], 400),
                ("GET", valid + "?alias=1", [("Host", host)], 400),
                ("GET", valid + "#alias", [("Host", host)], 400),
                ("GET", f"http://{host}/pool/%2e%2e/object.deb", [("Host", host)], 400),
                ("GET", f"http://{host}/../tmp/object.deb", [("Host", host)], 400),
                ("GET", f"http://{host}//tmp/object.deb", [("Host", host)], 400),
                ("GET", f"http://{host}/pool\\object.deb", [("Host", host)], 400),
                ("GET", valid, [("Host", host), ("Host", host)], 400),
                ("GET", valid, [("Host", host), ("Content-Length", "+0")], 400),
                ("GET", valid, [("Host", host), ("Content-Length", "1")], 400),
                (
                    "GET",
                    valid,
                    [("Host", host), ("Content-Length", "0"), ("Content-Length", "0")],
                    400,
                ),
                ("GET", valid, [("Host", host), ("Transfer-Encoding", "chunked")], 400),
                ("GET", valid, [("Host", host), ("Connection", "Host")], 400),
            )
            with running_proxy(self.module, root / "old", root / "new") as proxy:
                for method, target, headers, expected in cases:
                    with self.subTest(method=method, target=target, headers=headers):
                        response = raw_request(
                            proxy, request_bytes(method, target, headers)
                        )
                        self.assertEqual(statuses(response), [expected], response[:200])
            self.assertEqual(origin.request_count, 0)
            self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def run_subprocess_case(self, *, optimized: bool, **arguments):
        with tempfile.TemporaryDirectory(prefix="complete-run-case-") as tmp:
            root = pathlib.Path(tmp)
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.extend(
                [
                    str(self.runner),
                    "--module",
                    str(self.candidate),
                    "--old-cache",
                    str(root / "old"),
                    "--new-cache",
                    str(root / "new"),
                ]
            )
            for name, value in arguments.items():
                flag = "--" + name.replace("_", "-")
                command.extend([flag, str(value)])
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def test_normal_and_optimized_request_and_status_behavior_match(self):
        normal_invalid = self.run_subprocess_case(
            optimized=False,
            target_template="http://{host}/pool/object.deb?alias=1",
        )
        optimized_invalid = self.run_subprocess_case(
            optimized=True,
            target_template="http://{host}/pool/object.deb?alias=1",
        )
        for result, optimized in ((normal_invalid, False), (optimized_invalid, True)):
            self.assertEqual(result["optimized"], optimized)
            self.assertEqual([r["status"] for r in result["responses"]], [400])
            self.assertEqual(result["origin_requests"], 0)
            self.assertFalse(result["cache_exists"])
            self.assertEqual(result["temporary_paths"], [])

        for optimized in (False, True):
            rejected = self.run_subprocess_case(
                optimized=optimized,
                status=404,
                reason="Missing",
                body="origin-error",
                requests=2,
            )
            self.assertEqual(
                [r["status"] for r in rejected["responses"]], [502, 502]
            )
            self.assertEqual(rejected["origin_requests"], 2)
            self.assertFalse(rejected["cache_exists"])
            self.assertEqual(rejected["temporary_paths"], [])

        accepted = self.run_subprocess_case(
            optimized=True,
            status=200,
            reason="Mirror Success",
            body="accepted-body",
            requests=2,
        )
        self.assertEqual([r["status"] for r in accepted["responses"]], [200, 200])
        self.assertEqual(accepted["origin_requests"], 1)
        self.assertTrue(accepted["cache_exists"])
        self.assertEqual(accepted["cache_text"], "accepted-body")
        self.assertEqual(accepted["temporary_paths"], [])

    def test_request_headers_are_sanitized_and_safe_duplicates_survive(self):
        with running_http_server(FixedOrigin) as origin, tempfile.TemporaryDirectory(
            prefix="complete-headers-"
        ) as tmp:
            root = pathlib.Path(tmp)
            host = f"127.0.0.1:{origin.server_address[1]}"
            target = f"http://{host}/pool/headers.deb"
            headers = [
                ("Host", host),
                ("Proxy-Authorization", "Basic fake-only"),
                ("Proxy-Connection", "keep-alive"),
                ("Connection", "close, X-Hop"),
                ("X-Hop", "remove-me"),
                ("Keep-Alive", "timeout=5"),
                ("TE", "trailers"),
                ("Trailer", "X-Trailer"),
                ("Upgrade", "fake"),
                ("X-Safe", "one"),
                ("X-Safe", "two"),
                ("Content-Length", "0"),
            ]
            with running_proxy(self.module, root / "old", root / "new") as proxy:
                response = raw_request(proxy, request_bytes("GET", target, headers))
            self.assertEqual(statuses(response), [200])
            self.assertEqual(body_bytes(response), PAYLOAD)
            captured = origin.captured_headers[0]
            lowered = [(name.lower(), value) for name, value in captured]
            names = [name for name, _value in lowered]
            for blocked in (
                "proxy-authorization",
                "proxy-connection",
                "x-hop",
                "keep-alive",
                "te",
                "trailer",
                "upgrade",
            ):
                self.assertNotIn(blocked, names)
            self.assertEqual(
                [value for name, value in lowered if name == "x-safe"],
                ["one", "two"],
            )
            self.assertEqual(
                [value.lower() for name, value in lowered if name == "connection"],
                ["close"],
            )
            self.assertEqual(
                [value for name, value in lowered if name == "host"], [host]
            )

    def test_origin_framing_validation_and_retry(self):
        chunk_one = CHUNKED[:9]
        chunk_two = CHUNKED[9:]
        chunked = (
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Length: 999\r\n"
            b"Connection: close, X-Hop\r\n"
            b"X-Hop: remove\r\n"
            b"X-End-To-End: keep\r\n\r\n"
            + f"{len(chunk_one):X}\r\n".encode()
            + chunk_one
            + b"\r\n"
            + f"{len(chunk_two):X}\r\n".encode()
            + chunk_two
            + b"\r\n0\r\n\r\n"
        )
        invalids = (
            ("gzip", b"Transfer-Encoding: gzip\r\n", b"payload"),
            (
                "gzip-chunked",
                b"Transfer-Encoding: gzip, chunked\r\n",
                b"5\r\nhello\r\n0\r\n\r\n",
            ),
            ("plus", b"Content-Length: +5\r\n", b"hello"),
            ("comma", b"Content-Length: 5, 5\r\n", b"hello"),
            ("negative", b"Content-Length: -1\r\n", b"hello"),
        )
        with tempfile.TemporaryDirectory(prefix="complete-framing-") as tmp:
            root = pathlib.Path(tmp)
            with running_raw_server([chunked]) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/chunked.deb"
                with running_proxy(
                    self.module, root / "old-c", root / "new-c"
                ) as proxy:
                    response = raw_request(
                        proxy,
                        request_bytes(
                            "GET", target, [("Host", host), ("Connection", "close")]
                        ),
                    )
            self.assertEqual(statuses(response), [200])
            self.assertEqual(body_bytes(response), CHUNKED)
            downstream_headers = headers_bytes(response)
            self.assertNotIn(b"transfer-encoding:", downstream_headers)
            self.assertNotIn(b"content-length:", downstream_headers)
            self.assertNotIn(b"x-hop:", downstream_headers)
            self.assertIn(b"x-end-to-end: keep", downstream_headers)
            self.assertEqual(
                (root / "new-c/pool/chunked.deb").read_bytes(), CHUNKED
            )

            for label, framing, body in invalids:
                with self.subTest(label=label), running_raw_server(
                    [
                        b"HTTP/1.1 200 OK\r\n"
                        + framing
                        + b"Connection: close\r\n\r\n"
                        + body
                    ]
                ) as origin:
                    host = f"127.0.0.1:{origin.server_address[1]}"
                    target = f"http://{host}/pool/{label}.deb"
                    new_cache = root / f"new-{label}"
                    with running_proxy(
                        self.module, root / f"old-{label}", new_cache
                    ) as proxy:
                        response = raw_request(
                            proxy,
                            request_bytes(
                                "GET",
                                target,
                                [("Host", host), ("Connection", "close")],
                            ),
                        )
                    self.assertEqual(statuses(response), [502], response[:200])
                    final = new_cache / f"pool/{label}.deb"
                    self.assertFalse(final.exists())
                    if final.parent.exists():
                        wait_for_no_temporaries(final.parent)

            full = b"recovered-body"
            short = full[:5]
            responses = [
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(full)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + short,
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(full)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + full,
            ]
            with running_raw_server(responses) as origin:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/retry.deb"
                new_cache = root / "new-retry"
                with running_proxy(
                    self.module, root / "old-retry", new_cache
                ) as proxy:
                    first = raw_request(
                        proxy,
                        request_bytes(
                            "GET", target, [("Host", host), ("Connection", "close")]
                        ),
                    )
                    final = new_cache / "pool/retry.deb"
                    wait_for_no_temporaries(final.parent)
                    self.assertFalse(final.exists())
                    second = raw_request(
                        proxy,
                        request_bytes(
                            "GET", target, [("Host", host), ("Connection", "close")]
                        ),
                    )
            self.assertEqual(statuses(first), [200])
            self.assertEqual(statuses(second), [200])
            self.assertEqual(body_bytes(second), full)
            self.assertEqual(final.read_bytes(), full)
            self.assertEqual(origin.request_count, 2)

    def execute_scripted(self, factory, *, disconnect=False, fdopen=None):
        module = load_module(self.candidate, "lf_complete_scripted")
        stderr = io.StringIO()
        original_connection = module.http.client.HTTPConnection
        module.http.client.HTTPConnection = factory
        with tempfile.TemporaryDirectory(prefix="complete-scripted-") as tmp:
            root = pathlib.Path(tmp)
            try:
                patcher = (
                    mock.patch.object(module.os, "fdopen", fdopen)
                    if fdopen is not None
                    else contextlib.nullcontext()
                )
                with patcher, contextlib.redirect_stderr(stderr), running_proxy(
                    module, root / "old", root / "new", disconnect=disconnect
                ) as proxy:
                    target = "http://origin.invalid/pool/pkg.deb"
                    response = raw_request(
                        proxy,
                        request_bytes(
                            "GET",
                            target,
                            [
                                ("Host", "origin.invalid"),
                                ("Connection", "close"),
                                ("Content-Length", "0"),
                            ],
                        ),
                    )
            finally:
                module.http.client.HTTPConnection = original_connection
            files = [path for path in (root / "new").rglob("*") if path.is_file()]
            return response, stderr.getvalue(), files

    def test_post_commit_errors_emit_one_status_and_publish_nothing(self):
        response, stderr, files = self.execute_scripted(
            ConnectionFactory(error=ConnectionError("injected pre-commit failure"))
        )
        self.assertEqual(statuses(response), [502])
        self.assertIn("injected pre-commit failure", stderr)
        self.assertEqual(files, [])

        response, stderr, files = self.execute_scripted(
            ConnectionFactory(
                ScriptedResponse(
                    [PREFIX, RuntimeError("injected origin read failure")]
                )
            )
        )
        self.assertEqual(statuses(response), [200])
        self.assertIn(PREFIX, response)
        self.assertIn("injected origin read failure", stderr)
        self.assertEqual(files, [])

        def failing_fdopen(descriptor, *_args, **_kwargs):
            os.close(descriptor)
            raise OSError("injected cache writer failure")

        response, stderr, files = self.execute_scripted(
            ConnectionFactory(ScriptedResponse([PREFIX, b""])),
            fdopen=failing_fdopen,
        )
        self.assertEqual(statuses(response), [200])
        self.assertIn("injected cache writer failure", stderr)
        self.assertEqual(files, [])

        response, stderr, files = self.execute_scripted(
            ConnectionFactory(ScriptedResponse([PREFIX, b""])),
            disconnect=True,
        )
        self.assertEqual(statuses(response), [200])
        self.assertIn("injected downstream disconnect", stderr)
        self.assertEqual(files, [])

    def test_concurrent_misses_hide_final_name_and_clean_up(self):
        with tempfile.TemporaryDirectory(prefix="complete-concurrent-") as tmp:
            root = pathlib.Path(tmp)
            new_cache = root / "new"
            control = root / "control"
            control.write_bytes(b"control")
            expected_mode = stat.S_IMODE(control.stat().st_mode)
            with running_http_server(AtomicOrigin) as origin, running_proxy(
                self.module, root / "old", new_cache
            ) as proxy, concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                host = f"127.0.0.1:{origin.server_address[1]}"
                target = f"http://{host}/pool/atomic.deb"
                request = request_bytes(
                    "GET", target, [("Host", host), ("Connection", "close")]
                )
                first = pool.submit(raw_request, proxy, request)
                self.assertTrue(origin.atomic_started.wait(timeout=5))
                final = new_cache / "pool/atomic.deb"
                self.assertFalse(final.exists())
                second = pool.submit(raw_request, proxy, request)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    with origin.lock:
                        if origin.request_count >= 2:
                            break
                    time.sleep(0.02)
                else:
                    raise AssertionError("second miss did not reach origin")
                self.assertFalse(final.exists())
                origin.atomic_release.set()
                responses = [future.result(timeout=10) for future in (first, second)]
            self.assertEqual([statuses(value) for value in responses], [[200], [200]])
            self.assertEqual(
                [body_bytes(value) for value in responses], [PAYLOAD, PAYLOAD]
            )
            wait_for_cache(final, len(PAYLOAD))
            self.assertEqual(final.read_bytes(), PAYLOAD)
            self.assertEqual(stat.S_IMODE(final.stat().st_mode), expected_mode)
            wait_for_no_temporaries(final.parent)
            self.assertEqual(origin.request_count, 2)


if __name__ == "__main__":
    unittest.main()
