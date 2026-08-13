#!/usr/bin/env python3

from pathlib import Path
import argparse


def insert_before_xlib(source: str, name: str) -> str:
    needle = '  } else if (a_1 == "vkAcquireXlibDisplayEXT"sv) {'
    entry = (
        f'  }} else if (a_1 == "{name}"sv) {{\n'
        f'    return (PFN_vkVoidFunction)fexfn_impl_libvulkan_{name};\n'
    )
    if entry in source:
        return source
    if needle not in source:
        raise RuntimeError("custom lookup insertion point missing")
    return source.replace(needle, entry + needle, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host_cpp", type=Path)
    parser.add_argument("mode", choices=("report", "family"))
    args = parser.parse_args()

    source = args.host_cpp.read_text()
    source = insert_before_xlib(source, "vkCreateDebugReportCallbackEXT")

    if args.mode == "family":
        source = insert_before_xlib(source, "vkDestroyDebugReportCallbackEXT")
        source = insert_before_xlib(source, "vkCreateDebugUtilsMessengerEXT")

    args.host_cpp.write_text(source)


if __name__ == "__main__":
    main()
