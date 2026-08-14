# NODELETE guest-thunk build matrix

## Generic policy under test

All runs in this checkpoint inject the same candidate policy into the shared guest-thunk helper:

```cmake
if (TARGET_TYPE STREQUAL "SHARED")
  target_link_options(${NAME}-guest PRIVATE "LINKER:-z,nodelete")
endif()
```

The source-only candidate carrying this policy lives on owned fork branch `ci/nodelete-guest-thunk-policy-20260814`.

## Complete current 64-bit shared guest-thunk set

Hosted ARM64 run `31772954193`, job `94682444896`, artifact `9208823054`, FEX carrier commit `1a7446a64001ebdcab31e78e2ea077cc60649c75` completed successfully.

The run builds every current shared target emitted by `ThunkLibs/GuestLibs/CMakeLists.txt` for `BITNESS=64`:

- `asound-guest`
- `vulkan-guest`
- `drm-guest`
- `wayland-client-guest`
- `VDSO-guest`
- `GL-guest`
- `EGL-guest`
- `cuda-guest`

All eight outputs are real x86-64 FEX guest DSOs and preserve their expected SONAME while carrying `FLAGS_1: NODELETE`:

```text
libasound.so.2                      FLAGS_1: NODELETE
libvulkan.so.1                      FLAGS_1: NODELETE
libdrm.so.2                         FLAGS_1: NODELETE
libwayland-client.so.0.20.0         FLAGS_1: NODELETE
linux-vdso.so.1                     FLAGS_1: NODELETE
libGL.so.1                          FLAGS_1: NODELETE
libEGL.so.1                         FLAGS_1: NODELETE
libcuda.so.1                        FLAGS_1: NODELETE
```

This includes VDSO's special `-nostdlib`, static-PIE-style link and therefore exercises the unusual linker-option combination present in the central helper.

## 32-bit guest-thunk evidence

Hosted ARM64 run `31772868129`, job `94682195019`, artifact `9208785531`, FEX carrier commit `72339f6dfc8889c373cb8d3042ece5eaf410b386` configured the real `BITNESS=32` guest-thunk build with FEX's own `toolchain_x86_32.cmake` and built `wayland-client-guest` successfully.

The actual link command contains the expected policy alongside the existing 32-bit hardening/link flags:

```text
/usr/bin/x86_64-linux-gnu-g++ -m32 ...
  -Wl,-z,nodelete
  -Wl,-z,now
  -Wl,-z,relro
  -Wl,-z,notext
  -Wl,-soname,libwayland-client.so.0.20.0
  -shared -o libwayland-client-guest.so ...
```

The resulting binary is:

```text
ELF 32-bit LSB shared object, Intel 80386
SONAME: libwayland-client.so.0.20.0
FLAGS: BIND_NOW
FLAGS_1: NOW NODELETE
```

The workflow status was red only because its SONAME verification used an exact whitespace-sensitive `readelf` grep. The configure, thunk generation, compile, and link all succeeded, and the retained artifact contains the verified 32-bit NODELETE DSO. A follow-up green rerun uses a whitespace-independent SONAME assertion.

## Result

The central `add_guest_lib()` location has compile/link evidence across:

- every current 64-bit shared guest thunk target;
- the special VDSO link mode;
- FEX's real 32-bit guest toolchain on a callback-heavy Wayland wrapper.

No library-specific NODELETE exception has appeared.

All CI/source edits described here are diagnostic work on owned fork/investigation surfaces. No upstream FEX interaction occurred.
