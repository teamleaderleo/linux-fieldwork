#!/usr/bin/env python3
import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DEVICE_DISPATCH = {"VkDevice", "VkQueue", "VkCommandBuffer"}
INSTANCE_DISPATCH = {"VkInstance", "VkPhysicalDevice"}
PLUMBING = {
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
    return {name for name, _ in pattern.findall(interface_text)} - PLUMBING


def common_lookup_functions(host_text: str) -> set[str]:
    start = host_text.index("static PFN_vkVoidFunction LookupCustomVulkanFunction")
    end = host_text.index("return nullptr;", start)
    return set(re.findall(r'a_1\s*==\s*"([^"]+)"', host_text[start:end]))


def command_scopes(vk_xml: Path) -> dict[str, str]:
    root = ET.parse(vk_xml).getroot()
    scopes = {}
    for command in root.findall("./commands/command"):
        alias = command.get("alias")
        name_attr = command.get("name")
        if alias and name_attr:
            # Aliases have the same first-dispatch-object class as their target.
            scopes[name_attr] = ("alias", alias)
            continue
        proto = command.find("proto")
        if proto is None:
            continue
        name_node = proto.find("name")
        if name_node is None or not name_node.text:
            continue
        params = command.findall("param")
        if not params:
            scopes[name_node.text] = "global"
            continue
        type_node = params[0].find("type")
        first_type = type_node.text if type_node is not None else None
        if first_type in DEVICE_DISPATCH:
            scopes[name_node.text] = "device"
        elif first_type in INSTANCE_DISPATCH:
            scopes[name_node.text] = "instance"
        else:
            scopes[name_node.text] = "global"

    unresolved = True
    while unresolved:
        unresolved = False
        for name, value in list(scopes.items()):
            if isinstance(value, tuple):
                _, target = value
                target_scope = scopes.get(target)
                if isinstance(target_scope, str):
                    scopes[name] = target_scope
                    unresolved = True
    return scopes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("interface", type=Path)
    parser.add_argument("host", type=Path)
    parser.add_argument("vk_xml", type=Path)
    args = parser.parse_args()

    custom = custom_host_functions(args.interface.read_text())
    common = common_lookup_functions(args.host.read_text())
    scopes = command_scopes(args.vk_xml)

    print("custom_host_impl proc-address scope audit")
    print("name scope in-common-lookup")
    for name in sorted(custom):
        print(f"{name} {scopes.get(name, 'unknown')} {'yes' if name in common else 'no'}")

    missing_instance = sorted(name for name in custom if scopes.get(name) == "instance" and name not in common)
    missing_device = sorted(name for name in custom if scopes.get(name) == "device" and name not in common)
    common_nondevice = sorted(name for name in common if scopes.get(name) != "device")

    print("\ninstance custom implementations absent from common lookup:")
    for name in missing_instance:
        print(f"  {name}")
    print("device custom implementations absent from common lookup:")
    for name in missing_device:
        print(f"  {name}")
    print("common lookup entries that are not device-level commands:")
    for name in common_nondevice:
        print(f"  {name} ({scopes.get(name, 'unknown')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
