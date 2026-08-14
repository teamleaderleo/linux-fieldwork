#!/usr/bin/env python3
"""Inventory Vulkan VkAllocationCallbacks exposure in a FEX source checkout.

This is a scope audit, not a pass/fail product test. It combines the pinned
Vulkan header prototypes with FEX's per-ABI custom_host_impl metadata and prints
which allocator-taking commands are custom mediated versus generic.

Usage:
    python3 audit_vulkan_allocator_surface.py /path/to/FEX
"""

from __future__ import annotations

import argparse
import pathlib
import re


def select_abi(text: str, is_32bit: bool) -> str:
    """Evaluate direct IS_32BIT_THUNK conditionals and retain unknown ones."""
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


def allocator_commands(headers_dir: pathlib.Path) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {}
    prototype = re.compile(
        r"VKAPI_ATTR\s+.*?\s+VKAPI_CALL\s+(vk[A-Za-z0-9_]+)\s*\((.*?)\)\s*;",
        re.S,
    )
    for path in sorted(headers_dir.glob("vulkan*.h")):
        text = path.read_text(errors="replace")
        for match in prototype.finditer(text):
            name, params = match.groups()
            if "VkAllocationCallbacks" not in params:
                continue
            commands.setdefault(name, []).append(path.name)
    return commands


def counterpart(name: str) -> str | None:
    if name.startswith("vkCreate"):
        return "vkDestroy" + name[len("vkCreate") :]
    if name.startswith("vkDestroy"):
        return "vkCreate" + name[len("vkDestroy") :]
    if name.startswith("vkAllocate"):
        return "vkFree" + name[len("vkAllocate") :]
    if name.startswith("vkFree"):
        return "vkAllocate" + name[len("vkFree") :]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fex_root", type=pathlib.Path)
    args = parser.parse_args()

    interface_path = args.fex_root / "ThunkLibs/libvulkan/libvulkan_interface.cpp"
    headers_dir = args.fex_root / "External/Vulkan-Headers/include/vulkan"
    interface = interface_path.read_text()
    commands = allocator_commands(headers_dir)

    print(f"allocator-taking Vulkan commands found: {len(commands)}")
    print()

    for label, is_32bit in (("x86_64", False), ("x86_32", True)):
        custom = custom_host_impls(interface, is_32bit)
        mediated = sorted(name for name in commands if name in custom)
        generic = sorted(name for name in commands if name not in custom)

        print(f"[{label}]")
        print(f"custom_host_impl allocator commands: {len(mediated)}")
        for name in mediated:
            print(f"  custom  {name}")
        print(f"generic allocator commands: {len(generic)}")
        for name in generic:
            print(f"  generic {name}")

        asymmetries: list[tuple[str, str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for name in commands:
            other = counterpart(name)
            if not other or other not in commands:
                continue
            pair = tuple(sorted((name, other)))
            if pair in seen:
                continue
            seen.add(pair)
            a, b = pair
            a_status = "custom" if a in custom else "generic"
            b_status = "custom" if b in custom else "generic"
            if a_status != b_status:
                asymmetries.append((a, a_status, b, b_status))

        print(f"paired custom/generic asymmetries: {len(asymmetries)}")
        for a, a_status, b, b_status in sorted(asymmetries):
            print(f"  {a}={a_status}  {b}={b_status}")
        print()

    duplicates = {name: files for name, files in commands.items() if len(files) > 1}
    if duplicates:
        print("header duplicates (deduplicated by command name):")
        for name, files in sorted(duplicates.items()):
            print(f"  {name}: {', '.join(files)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
