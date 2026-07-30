#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import types


def load_base_composer(repo_root: pathlib.Path) -> types.ModuleType:
    path = repo_root / "investigations/caching-proxy-composed-stack/compose.py"
    spec = importlib.util.spec_from_file_location("lf_caching_proxy_base_composer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base composer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def compose(repo_root: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    repo_root = repo_root.resolve()
    base = load_base_composer(repo_root)
    candidate = base.compose(repo_root, destination)
    text = candidate.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        assert int(self.headers.get("Content-Length", 0)) == 0
''',
        '''class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        response_started = False
        assert int(self.headers.get("Content-Length", 0)) == 0
''',
        "response state",
    )

    text = replace_once(
        text,
        '''            headers = downstream_headers(res)
            self.wfile.write(b"HTTP/1.1 200 OK\\r\\n")
''',
        '''            headers = downstream_headers(res)
            response_started = True
            self.wfile.write(b"HTTP/1.1 200 OK\\r\\n")
''',
        "fresh response commitment",
    )

    text = replace_once(
        text,
        '''        except Exception as e:
            self.send_error(502)
''',
        '''        except Exception as error:
            print(f"proxy request failed: {error!r}", file=sys.stderr)
            if response_started:
                self.close_connection = True
                return
            self.send_error(502)
''',
        "streaming error disposition",
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
