#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

# Custom entrypoints that are implementation plumbing rather than Vulkan names
# which an application can obtain through vkGetInstanceProcAddr/vkGetDeviceProcAddr.
EXEMPT = {
    "vkGetDeviceProcAddr",
    "vkGetInstanceProcAddr",
    "Vulkan_SetGuestXSync",
    "Vulkan_SetGuestXGetVisualInfo",
    "Vulkan_SetGuestXDisplayString",
}


def custom_host_functions(interface_text: str) -> set[str]:
    pattern = re.compile(
        r"struct\s+fex_gen_config<([A-Za-z0-9_]+)>\s*:\s*([^;]*\bcustom_host_impl\b[^;]*)\{\};"
    )
    return {name for name, _ in pattern.findall(interface_text)}


def lookup_functions(host_text: str) -> set[str]:
    start = host_text.index("static PFN_vkVoidFunction LookupCustomVulkanFunction")
    end = host_text.index("return nullptr;", start)
    body = host_text[start:end]
    return set(re.findall(r'a_1\s*==\s*"([^"]+)"', body))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interface", type=Path)
    parser.add_argument("host", type=Path)
    parser.add_argument("--expect-missing", nargs="*", default=None)
    args = parser.parse_args()

    custom = custom_host_functions(args.interface.read_text())
    lookup = lookup_functions(args.host.read_text())
    missing = sorted(custom - lookup - EXEMPT)
    extra = sorted(lookup - custom)

    print("custom_host_impl:")
    for name in sorted(custom):
        print(f"  {name}")
    print("lookup registrations:")
    for name in sorted(lookup):
        print(f"  {name}")
    print("missing custom lookup registrations:")
    for name in missing:
        print(f"  {name}")
    print("lookup entries without custom_host_impl:")
    for name in extra:
        print(f"  {name}")

    if args.expect_missing is not None:
        expected = sorted(args.expect_missing)
        if missing != expected:
            print(f"expected missing={expected}, actual={missing}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
