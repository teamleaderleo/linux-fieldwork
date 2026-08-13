#!/usr/bin/env python3
"""Compare Vulkan custom_host_impl declarations with dynamic custom lookup.

Run against a FEX source checkout:

    python3 audit_custom_vulkan_lookup.py /path/to/FEX

Exit status is 0 when each ABI's internal custom_host_impl set matches the
entries in LookupCustomVulkanFunction(), and 1 when a mismatch exists.
"""

import argparse
import pathlib
import re
import sys


def select_abi(text: str, is_32bit: bool) -> str:
    """Evaluate only IS_32BIT_THUNK conditional branches.

    Other preprocessor conditionals are retained. The Vulkan declarations and
    lookup list use direct IS_32BIT_THUNK branches for the ABI differences this
    audit needs to classify.
    """
    out: list[str] = []
    active = [True]
    known: list[bool] = []

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        match = re.fullmatch(r"#\s*(ifdef|ifndef)\s+IS_32BIT_THUNK", stripped)
        if match:
            condition = is_32bit if match.group(1) == "ifdef" else not is_32bit
            active.append(active[-1] and condition)
            known.append(True)
            continue

        if stripped.startswith("#if"):
            active.append(active[-1])
            known.append(False)
            if active[-1]:
                out.append(line)
            continue

        if stripped.startswith("#else") and len(active) > 1:
            if known[-1]:
                parent = active[-2]
                active[-1] = parent and not active[-1]
            elif active[-1]:
                out.append(line)
            continue

        if stripped.startswith("#endif") and len(active) > 1:
            was_known = known.pop()
            active.pop()
            if not was_known and active[-1]:
                out.append(line)
            continue

        if active[-1]:
            out.append(line)

    return "".join(out)


def internal_region(text: str) -> str:
    start = text.index("namespace internal {")
    end = text.index("} // namespace internal", start)
    return text[start:end]


def custom_host_impls(interface: str, is_32bit: bool) -> set[str]:
    text = internal_region(select_abi(interface, is_32bit))
    pattern = re.compile(
        r"struct\s+fex_gen_config<([A-Za-z_][A-Za-z0-9_]*)>\s*:\s*"
        r"([^{};]*\bcustom_host_impl\b[^{};]*)\{\s*\}\s*;",
        re.S,
    )
    return {match.group(1) for match in pattern.finditer(text)}


def lookup_entries(host: str, is_32bit: bool) -> set[str]:
    text = select_abi(host, is_32bit)
    start = text.index("static PFN_vkVoidFunction LookupCustomVulkanFunction")
    end = text.index("return nullptr;", start)
    body = text[start:end]
    return set(re.findall(r'a_1\s*==\s*"([A-Za-z_][A-Za-z0-9_]*)"sv', body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fex_root", type=pathlib.Path)
    args = parser.parse_args()

    interface = (
        args.fex_root / "ThunkLibs/libvulkan/libvulkan_interface.cpp"
    ).read_text()
    host = (args.fex_root / "ThunkLibs/libvulkan/Host.cpp").read_text()

    failed = False
    for label, is_32bit in (("x86_64", False), ("x86_32", True)):
        custom = custom_host_impls(interface, is_32bit)
        lookup = lookup_entries(host, is_32bit)
        missing = sorted(custom - lookup)
        lookup_only = sorted(lookup - custom)

        print(f"{label}: custom_host_impl={len(custom)} lookup={len(lookup)}")
        print("  missing:", ", ".join(missing) if missing else "(none)")
        print(
            "  lookup-only:",
            ", ".join(lookup_only) if lookup_only else "(none)",
        )
        failed |= bool(missing or lookup_only)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
