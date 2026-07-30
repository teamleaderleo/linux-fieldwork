#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import types


def load_implementation() -> types.ModuleType:
    path = pathlib.Path(__file__).with_name("compose_impl.py")
    spec = importlib.util.spec_from_file_location(
        "lf_caching_proxy_complete_stack_impl", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load composer implementation: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_impl = load_implementation()
_original_repairs = _impl.REQUIRED_REPAIRS
REQUIRED_REPAIRS = (
    *_original_repairs[:4],
    "investigations/caching-proxy-complete-stack/inputs/0001-confine-cache-paths.patch",
    "investigations/caching-proxy-complete-stack/inputs/0002-reject-nondecimal-content-length.patch",
    "investigations/caching-proxy-complete-stack/inputs/0003-close-after-committed-response-errors.patch",
    "investigations/caching-proxy-complete-stack/inputs/0004-check-origin-status-at-runtime.patch",
)
REQUIRED_PATCH_MARKERS = {
    new: _impl.REQUIRED_PATCH_MARKERS[old]
    for new, old in zip(REQUIRED_REPAIRS, _original_repairs)
}
_impl.REQUIRED_REPAIRS = REQUIRED_REPAIRS
_impl.REQUIRED_PATCH_MARKERS = REQUIRED_PATCH_MARKERS
compose = _impl.compose
verify_repair_artifacts = _impl.verify_repair_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(compose(args.repo_root, args.destination))


if __name__ == "__main__":
    main()
