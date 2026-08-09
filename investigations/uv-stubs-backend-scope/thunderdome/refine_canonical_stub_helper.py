from __future__ import annotations

import pathlib
import sys


OLD = '''fn simple_stub_module_dir(package: &PackageName) -> Option<String> {
    package
        .as_dist_info_name()
        .strip_suffix("_stubs")
        .map(|stem| format!("{stem}-stubs"))
}'''

NEW = '''fn simple_stub_module_dir(package: &PackageName) -> Option<String> {
    package
        .as_str()
        .strip_suffix("-stubs")
        .map(|_| package.to_string())
}'''


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: refine_canonical_stub_helper.py <uv init.rs>")
    path = pathlib.Path(sys.argv[1])
    text = path.read_text()
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f"canonical stub helper: expected one match, found {count}")
    path.write_text(text.replace(OLD, NEW, 1))


if __name__ == "__main__":
    main()
