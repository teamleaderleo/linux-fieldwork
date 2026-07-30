#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.client
import http.server
import importlib.util
import json
import pathlib
import threading
import types


def load_module(path: pathlib.Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("lf_origin_status_proxy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def running_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("server thread survived shutdown")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=pathlib.Path, required=True)
    parser.add_argument("--old-cache", type=pathlib.Path, required=True)
    parser.add_argument("--new-cache", type=pathlib.Path, required=True)
    parser.add_argument("--status", type=int, required=True)
    parser.add_argument("--body", required=True)
    args = parser.parse_args()

    body = args.body.encode("utf-8")

    class Origin(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.server.request_count += 1
            self.send_response(args.status)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_values):
            return

    origin = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Origin)
    origin.request_count = 0

    module = load_module(args.module)
    args.old_cache.mkdir(parents=True, exist_ok=True)
    args.new_cache.mkdir(parents=True, exist_ok=True)
    module.oldcachedir = args.old_cache
    module.newcachedir = args.new_cache
    module.readonly = False

    class Proxy(module.ProxyRequestHandler):
        def log_message(self, _format, *_values):
            return

    proxy = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Proxy)

    with running_server(origin), running_server(proxy):
        host = f"127.0.0.1:{origin.server_address[1]}"
        target = f"http://{host}/pool/object.deb"
        connection = http.client.HTTPConnection(
            "127.0.0.1", proxy.server_address[1], timeout=5
        )
        connection.request(
            "GET", target, headers={"Host": host, "Connection": "close"}
        )
        response = connection.getresponse()
        downstream = response.read()
        response_status = response.status
        connection.close()

    cached = args.new_cache / "pool/object.deb"
    cached_bytes = cached.read_bytes() if cached.exists() else b""
    temporaries = sorted(
        str(path.relative_to(args.new_cache))
        for path in args.new_cache.rglob("*")
        if path.name.startswith(".")
    )
    print(
        json.dumps(
            {
                "optimized": not __debug__,
                "origin_status": args.status,
                "origin_requests": origin.request_count,
                "downstream_status": response_status,
                "downstream_sha256": hashlib.sha256(downstream).hexdigest(),
                "downstream_text": downstream.decode("utf-8", errors="replace"),
                "cache_exists": cached.exists(),
                "cache_sha256": hashlib.sha256(cached_bytes).hexdigest(),
                "cache_text": cached_bytes.decode("utf-8", errors="replace"),
                "temporary_paths": temporaries,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
