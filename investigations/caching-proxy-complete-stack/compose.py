#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess


REQUIRED_REPAIRS = (
    "investigations/caching-proxy-atomic-publication/0001-publish-cache-files-atomically.patch",
    "investigations/caching-proxy-hop-by-hop-framing/0001-normalize-downstream-framing.patch",
    "investigations/caching-proxy-content-length/0001-reject-short-upstream-responses.patch",
    "investigations/caching-proxy-request-hop-headers/0001-filter-origin-request-headers.patch",
    "investigations/mmdebstrap-caching-proxy-containment/0001-confine-cache-paths.patch",
    "investigations/mmdebstrap-caching-proxy-containment/0002-reject-nondecimal-content-length.patch",
    "investigations/caching-proxy-post-commit-errors/0001-close-after-committed-response-errors.patch",
    "investigations/caching-proxy-origin-status/0001-check-origin-status-at-runtime.patch",
)

REQUIRED_PATCH_MARKERS = {
    REQUIRED_REPAIRS[0]: (
        "def cache_destination(path):",
        "os.O_WRONLY | os.O_CREAT | os.O_EXCL",
        "0o666",
    ),
    REQUIRED_REPAIRS[1]: (
        "def downstream_headers(response):",
        'self.send_header("Connection", "close")',
    ),
    REQUIRED_REPAIRS[2]: (
        'expected_length = res.getheader("Content-Length")',
        "received != expected_length",
        "http.client.IncompleteRead",
    ),
    REQUIRED_REPAIRS[3]: (
        "def origin_request_headers(headers):",
        '"proxy-authorization"',
        "headers.raw_items()",
    ),
    REQUIRED_REPAIRS[4]: (
        "def cache_path(root, request_target, host):",
        'or "%" in raw_path',
        "candidate.is_relative_to(root)",
        'server_address=("127.0.0.1", 8080)',
    ),
    REQUIRED_REPAIRS[5]: (
        'character not in "0123456789"',
        'self.send_error(400, "invalid Content-Length")',
    ),
    REQUIRED_REPAIRS[6]: (
        "response_started = False",
        "if response_started:",
        "self.close_connection = True",
    ),
    REQUIRED_REPAIRS[7]: (
        "if res.status != 200:",
        "unexpected upstream response",
    ),
}

HELPERS = '''HOP_BY_HOP_REQUEST_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

HOP_BY_HOP_RESPONSE_HEADERS = HOP_BY_HOP_REQUEST_HEADERS


def request_context(root, request_target, host):
    parsed = urllib.parse.urlsplit(request_target)
    try:
        host_parsed = urllib.parse.urlsplit("//" + host)
        request_port = parsed.port or 80
        host_port = host_parsed.port or 80
    except ValueError as error:
        raise ValueError("invalid proxy request target") from error
    if (
        parsed.scheme.lower() != "http"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname is None
        or host_parsed.username is not None
        or host_parsed.password is not None
        or host_parsed.hostname is None
        or host_parsed.path
        or host_parsed.query
        or host_parsed.fragment
        or parsed.hostname.lower() != host_parsed.hostname.lower()
        or request_port != host_port
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise ValueError("invalid proxy request target")
    raw_path = parsed.path[1:]
    if not raw_path or "%" in raw_path or "\\\\" in raw_path or "\\0" in raw_path:
        raise ValueError("unsafe cache path")
    components = raw_path.split("/")
    if any(part in ("", ".", "..") for part in components):
        raise ValueError("unsafe cache path")
    relative = pathlib.PurePosixPath(*components)
    resolved_root = root.resolve()
    candidate = (resolved_root / pathlib.Path(*relative.parts)).resolve()
    if candidate == resolved_root or not candidate.is_relative_to(resolved_root):
        raise ValueError("unsafe cache path")
    return candidate, parsed.hostname, request_port


def origin_request_headers(headers):
    connection_tokens = set()
    for value in headers.get_all("Connection", []):
        connection_tokens.update(
            token.strip().lower()
            for token in value.split(",")
            if token.strip()
        )
    if "host" in connection_tokens:
        raise ValueError("Host cannot be a connection-specific field")
    blocked = HOP_BY_HOP_REQUEST_HEADERS | connection_tokens
    result = [
        (name, value)
        for name, value in headers.raw_items()
        if name.lower() not in blocked
    ]
    result.append(("Connection", "close"))
    return result


def validate_transfer_encoding(response):
    values = response.headers.get_all("Transfer-Encoding", [])
    if not values:
        return
    tokens = [
        token.strip().lower()
        for value in values
        for token in value.split(",")
        if token.strip()
    ]
    if tokens != ["chunked"] or not response.chunked:
        raise ValueError("unsupported upstream Transfer-Encoding")


def downstream_headers(response):
    headers = response.getheaders()
    connection_tokens = set()
    for name, value in headers:
        if name.lower() == "connection":
            connection_tokens.update(
                token.strip().lower()
                for token in value.split(",")
                if token.strip()
            )
    blocked = HOP_BY_HOP_RESPONSE_HEADERS | connection_tokens
    if response.chunked:
        blocked = blocked | {"content-length"}
    return [
        (name, value)
        for name, value in headers
        if name.lower() not in blocked
    ]
'''

REQUEST_SETUP = '''    def reject_method(self):
        self.send_error(405, "method not allowed")

    do_CONNECT = reject_method
    do_DELETE = reject_method
    do_HEAD = reject_method
    do_OPTIONS = reject_method
    do_PATCH = reject_method
    do_POST = reject_method
    do_PUT = reject_method
    do_TRACE = reject_method

    def do_GET(self):
        host_values = self.headers.get_all("Host", [])
        content_length_values = self.headers.get_all("Content-Length", [])
        if (
            len(host_values) != 1
            or len(content_length_values) > 1
            or self.headers.get_all("Transfer-Encoding", [])
        ):
            self.send_error(400, "invalid proxy request")
            return
        if content_length_values:
            content_length_text = content_length_values[0]
            if not content_length_text or any(
                character < "0" or character > "9"
                for character in content_length_text
            ):
                self.send_error(400, "invalid Content-Length")
                return
            content_length = int(content_length_text)
        else:
            content_length = 0
        if content_length != 0:
            self.send_error(400, "invalid proxy request")
            return

        host = host_values[0]
        try:
            oldpath, origin_host, origin_port = request_context(
                oldcachedir, self.path, host
            )
            newpath, second_host, second_port = request_context(
                newcachedir, self.path, host
            )
            if (origin_host, origin_port) != (second_host, second_port):
                raise ValueError("inconsistent proxy request authority")
            origin_headers = origin_request_headers(self.headers)
        except ValueError as error:
            self.send_error(400, str(error))
            return
'''

FRESH_BLOCK = '''        # download fresh copy
        response_started = False
        conn = None
        try:
            print(f"\\rproxy download: {self.path}", file=sys.stderr)
            conn = http.client.HTTPConnection(
                origin_host, origin_port, timeout=5
            )
            conn.putrequest(
                "GET", self.path, skip_host=True, skip_accept_encoding=True
            )
            for name, value in origin_headers:
                conn.putheader(name, value)
            conn.endheaders()
            res = conn.getresponse()
            if res.status != 200:
                raise http.client.HTTPException(
                    f"unexpected upstream response: {res.status} {res.reason}"
                )
            validate_transfer_encoding(res)
            expected_length = (
                None if res.chunked else res.getheader("Content-Length")
            )
            if expected_length is not None:
                if not expected_length or any(
                    character < "0" or character > "9"
                    for character in expected_length
                ):
                    raise ValueError("invalid upstream Content-Length")
                expected_length = int(expected_length)
            headers = downstream_headers(res)
            response_started = True
            self.wfile.write(b"HTTP/1.1 200 OK\\r\\n")
            for name, value in headers:
                self.send_header(name, value)
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            with cache_destination(newpath) as cache:
                received = 0
                while True:
                    buf = res.read(64 * 1024)  # same as shutil uses
                    if not buf:
                        break
                    self.wfile.write(buf)
                    cache.write(buf)
                    received += len(buf)
                    time.sleep(64 / 1024)  # 1024 kB/s
                if expected_length is not None and received != expected_length:
                    raise http.client.IncompleteRead(
                        b"", expected_length - received
                    )
            self.wfile.flush()
        except Exception as error:
            print(f"proxy error: {error!r}", file=sys.stderr)
            if response_started:
                self.close_connection = True
                return
            self.send_error(502)
        finally:
            if conn is not None:
                conn.close()
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def verify_repair_artifacts(repo_root: pathlib.Path) -> None:
    for relative in REQUIRED_REPAIRS:
        patch = repo_root / relative
        if not patch.is_file():
            raise RuntimeError(f"missing canonical repair: {relative}")
        content = patch.read_text(encoding="utf-8")
        for marker in REQUIRED_PATCH_MARKERS[relative]:
            if marker not in content:
                raise RuntimeError(
                    f"canonical repair contract drifted: {relative}: {marker}"
                )


def compose(repo_root: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    repo_root = repo_root.resolve()
    source = repo_root / "upstream/mmdebstrap/caching_proxy.py"
    verify_repair_artifacts(repo_root)

    candidate_root = destination.resolve()
    candidate = candidate_root / "upstream/mmdebstrap/caching_proxy.py"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, candidate)

    atomic_patch = repo_root / REQUIRED_REPAIRS[0]
    applied = subprocess.run(
        ["patch", "--batch", "--forward", "-p1", "-i", str(atomic_patch)],
        cwd=candidate_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if applied.returncode != 0:
        raise RuntimeError(applied.stdout + applied.stderr)

    text = candidate.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "readonly = False\n\n\ndef new_cache_temporary",
        "readonly = False\n\n\n" + HELPERS + "\n\ndef new_cache_temporary",
        "full-stack helpers",
    )
    old_setup = '''    def do_GET(self):
        assert int(self.headers.get("Content-Length", 0)) == 0
        assert self.headers["Host"]
        pathprefix = "http://" + self.headers["Host"] + "/"
        assert self.path.startswith(pathprefix)
        sanitizedpath = urllib.parse.unquote(self.path.removeprefix(pathprefix))
        oldpath = oldcachedir / sanitizedpath
        newpath = newcachedir / sanitizedpath
'''
    text = replace_once(text, old_setup, REQUEST_SETUP, "request boundary")

    fresh_start = text.index("        # download fresh copy\n")
    fresh_end = text.index("\n\n\ndef main():", fresh_start)
    text = text[:fresh_start] + FRESH_BLOCK.rstrip() + text[fresh_end:]

    text = replace_once(
        text,
        'server_address=("", 8080), RequestHandlerClass=ProxyRequestHandler',
        'server_address=("127.0.0.1", 8080), RequestHandlerClass=ProxyRequestHandler',
        "loopback bind",
    )
    candidate.write_text(text, encoding="utf-8")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(compose(args.repo_root, args.destination))


if __name__ == "__main__":
    main()
