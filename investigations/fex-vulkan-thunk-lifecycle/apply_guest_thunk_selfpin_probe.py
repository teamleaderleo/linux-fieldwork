#!/usr/bin/env python3
"""Apply a conservative process-lifetime self-pin to normal FEX guest thunk DSOs.

The candidate uses each guest thunk's existing public ELF SONAME. During the
common LOAD_LIB constructor, the DSO opens that SONAME once more. The dynamic
loader resolves the already-loaded object and increments its loader reference
count, so ordinary application dlclose calls cannot unmap guest thunk code.

VDSO is intentionally excluded because its guest thunk is linked with
-nostdlib and has different lifetime semantics.
"""

from pathlib import Path
import argparse


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_cmake(path: Path) -> None:
    text = path.read_text()
    old = """  target_compile_definitions(${NAME}-guest PRIVATE GUEST_THUNK_LIBRARY)\n  target_link_libraries(${NAME}-guest PRIVATE lib${NAME}-guest-deps)\n"""
    new = """  target_compile_definitions(${NAME}-guest PRIVATE GUEST_THUNK_LIBRARY)\n  target_link_libraries(${NAME}-guest PRIVATE lib${NAME}-guest-deps)\n\n  # Guest thunk entrypoints and continuations are published outside the DSO's\n  # ordinary loader-handle lifetime. Keep normal guest thunk DSOs resident for\n  # the process once loaded. VDSO is freestanding and follows separate lifetime\n  # rules, so it is deliberately excluded.\n  if (NOT NAME STREQUAL \"VDSO\")\n    target_compile_definitions(${NAME}-guest PRIVATE\n      FEX_GUEST_THUNK_SELF_PIN=1\n      FEX_GUEST_THUNK_SONAME=\"${SONAME}\")\n    target_link_libraries(${NAME}-guest PRIVATE dl)\n  endif()\n"""
    path.write_text(replace_once(text, old, new, "guest thunk CMake lifetime policy"))


def patch_guest_header(path: Path) -> None:
    text = path.read_text()
    old_includes = """#pragma once\n#include <stdint.h>\n#include <type_traits>\n"""
    new_includes = """#pragma once\n#include <stdint.h>\n#include <type_traits>\n\n#if defined(FEX_GUEST_THUNK_SELF_PIN)\n#include <dlfcn.h>\n#endif\n"""
    text = replace_once(text, old_includes, new_includes, "Guest.h includes")

    old_macro = """#define LOAD_LIB_BASE(name, init_fn)                   \\\n  __attribute__((constructor)) static void loadlib() { \\\n    LoadlibArgs args = {#name};                        \\\n    fexthunks_fex_loadlib(&args);                      \\\n    if ((init_fn)) ((void (*)())init_fn)();            \\\n  }\n"""
    new_macro = """#if defined(FEX_GUEST_THUNK_SELF_PIN)\nstatic void PinGuestThunkForProcessLifetime() {\n  static void* const PinHandle = dlopen(FEX_GUEST_THUNK_SONAME, RTLD_LAZY | RTLD_LOCAL);\n  if (!PinHandle) {\n    __builtin_trap();\n  }\n}\n#else\nstatic void PinGuestThunkForProcessLifetime() {}\n#endif\n\n#define LOAD_LIB_BASE(name, init_fn)                   \\\n  __attribute__((constructor)) static void loadlib() { \\\n    LoadlibArgs args = {#name};                        \\\n    fexthunks_fex_loadlib(&args);                      \\\n    PinGuestThunkForProcessLifetime();                 \\\n    if ((init_fn)) ((void (*)())init_fn)();            \\\n  }\n"""
    path.write_text(replace_once(text, old_macro, new_macro, "LOAD_LIB self-pin"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fex_root", type=Path)
    args = parser.parse_args()
    root = args.fex_root.resolve()
    patch_cmake(root / "ThunkLibs/GuestLibs/CMakeLists.txt")
    patch_guest_header(root / "ThunkLibs/include/common/Guest.h")
    print("Applied guest thunk process-lifetime self-pin candidate")


if __name__ == "__main__":
    main()
