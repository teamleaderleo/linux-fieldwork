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
)

HEADER_HELPERS = '''HOP_BY_HOP_HEADERS = {
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
    blocked = HOP_BY_HOP_HEADERS | connection_tokens
    if response.chunked:
        blocked = blocked | {"content-length"}
    return [
        (name, value)
        for name, value in headers
        if name.lower() not in blocked
    ]
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def compose(repo_root: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    repo_root = repo_root.resolve()
    source = repo_root / "upstream/mmdebstrap/caching_proxy.py"
    for relative in REQUIRED_REPAIRS:
        if not (repo_root / relative).is_file():
            raise RuntimeError(f"missing canonical repair: {relative}")

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
        "readonly = False\n\n\n" + HEADER_HELPERS + "\n\ndef new_cache_temporary",
        "downstream header helpers",
    )

    text = replace_once(
        text,
        '''            res = conn.getresponse()
            assert (res.status, res.reason) == (200, "OK"), (res.status, res.reason)
            self.wfile.write(b"HTTP/1.1 200 OK\\r\\n")
            for k, v in res.getheaders():
                # do not allow a persistent connection
                if k == "connection":
                    continue
                self.send_header(k, v)
            self.end_headers()
            with cache_destination(newpath) as f:
''',
        '''            res = conn.getresponse()
            assert (res.status, res.reason) == (200, "OK"), (res.status, res.reason)
            # A Content-Length on a chunked response does not frame the decoded
            # bytes returned by http.client and must not be validated as such.
            expected_length = None if res.chunked else res.getheader("Content-Length")
            if expected_length is not None:
                expected_length = int(expected_length)
                if expected_length < 0:
                    raise ValueError("negative upstream Content-Length")
            headers = downstream_headers(res)
            self.wfile.write(b"HTTP/1.1 200 OK\\r\\n")
            for k, v in headers:
                self.send_header(k, v)
            self.send_header("Connection", "close")
            self.close_connection = True
            self.end_headers()
            with cache_destination(newpath) as f:
                received = 0
''',
        "fresh response setup",
    )

    text = replace_once(
        text,
        '''                    self.wfile.write(buf)
                    f.write(buf)
                    time.sleep(64 / 1024)  # 1024 kB/s
            self.wfile.flush()
''',
        '''                    self.wfile.write(buf)
                    f.write(buf)
                    received += len(buf)
                    time.sleep(64 / 1024)  # 1024 kB/s
                if expected_length is not None and received != expected_length:
                    raise http.client.IncompleteRead(
                        b"", expected_length - received
                    )
            self.wfile.flush()
''',
        "declared length validation",
    )

    candidate.write_text(text, encoding="utf-8")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    args = parser.parse_args()
    candidate = compose(args.repo_root, args.destination)
    print(candidate)


if __name__ == "__main__":
    main()
