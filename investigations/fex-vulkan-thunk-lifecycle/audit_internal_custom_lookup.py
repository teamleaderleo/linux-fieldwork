#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def internal_body(text: str) -> str:
    begin = text.index("namespace internal {")
    end = text.index("} // namespace internal", begin)
    return text[begin:end]


def custom_names(text: str) -> set[str]:
    body = internal_body(text)
    pattern = re.compile(
        r"struct\s+fex_gen_config<([A-Za-z0-9_]+)>\s*:\s*([^;]*\bcustom_host_impl\b[^;]*)\{\};"
    )
    return {name for name, _bases in pattern.findall(body)}


def lookup_names(text: str) -> set[str]:
    begin = text.index("static PFN_vkVoidFunction LookupCustomVulkanFunction")
    end = text.index("return nullptr;", begin)
    body = text[begin:end]
    return set(re.findall(r'a_1\s*==\s*"([^"]+)"', body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interface", type=Path)
    parser.add_argument("host", type=Path)
    parser.add_argument("--expect-missing", nargs="*", default=None)
    args = parser.parse_args()

    custom = custom_names(args.interface.read_text())
    lookup = lookup_names(args.host.read_text())
    missing = sorted(custom - lookup)
    extra = sorted(lookup - custom)

    print(f"internal custom_host_impl={len(custom)} lookup={len(lookup)}")
    print("missing:", ", ".join(missing) if missing else "-")
    print("extra:", ", ".join(extra) if extra else "-")

    if extra:
        return 1
    if args.expect_missing is not None and missing != sorted(args.expect_missing):
        print("expected missing:", ", ".join(sorted(args.expect_missing)) if args.expect_missing else "-")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
