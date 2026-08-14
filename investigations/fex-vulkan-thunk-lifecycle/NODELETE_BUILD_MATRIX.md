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

The first workflow status was red only because its SONAME verification used an exact whitespace-sensitive `readelf` grep. The configure, thunk generation, compile, and link all succeeded.

A corrected independent gate on owned branch `ci/agent-n-arm64-20260814`, commit `b8a5afea844ab3fb6f1d989f627660536255d7f9`, run `31773109794`, job `94682895383`, completed successfully with whitespace-independent verification. It confirms the real 32-bit Wayland wrapper is Intel 80386, carries the expected SONAME, and contains `FLAGS_1: NOW NODELETE`.

## Alternate guest linker gate

Owned branch `ci/agent-o-arm64-20260814`, commit `03091aa757df5c42af71c3b2c29e9b9f40ec2d0b`, run `31773697772`, job `94684644938`, artifact `9209088465`, completed successfully with FEX's `ENABLE_CLANG_THUNKS=ON` mode.

The real generated Vulkan guest wrapper linked through lld (`-fuse-ld=lld`), preserved `SONAME libvulkan.so.1`, and carried `FLAGS_1: NODELETE`. This verifies the central policy under both the default guest linker configuration and FEX's lld guest-thunk mode.

## Measured 64-bit wrapper residency footprint

A follow-up hosted ARM64 measurement run `31775283101`, artifact `9209667954`, FEX carrier commit `fde99a4d92cf41a902b40c7b0fb6cb07a86bf9e4` rebuilt the same eight real x86-64 shared guest wrappers with the generic NODELETE policy and recorded both on-disk ELF size and the sum of ELF `PT_LOAD` `p_memsz` values.

The measured wrapper-only totals are:

```text
WRAPPER_COUNT=8
FILE_BYTES_TOTAL=10598320
PT_LOAD_MEMSZ_TOTAL=1771423
FILE_MIB_TOTAL=10.107
PT_LOAD_MIB_TOTAL=1.689
```

Per wrapper:

| guest wrapper | ELF file bytes | summed PT_LOAD memsz bytes | direct NEEDED entries |
| --- | ---: | ---: | --- |
| asound | 1,076,888 | 257,381 | `libc.so.6` |
| vulkan | 2,255,776 | 294,421 | `libstdc++.so.6`, `libgcc_s.so.1`, `libc.so.6` |
| drm | 138,856 | 28,893 | `libc.so.6` |
| wayland-client | 266,568 | 30,529 | `libstdc++.so.6`, `libgcc_s.so.1`, `libc.so.6` |
| VDSO | 12,072 | 2,008 | none |
| GL | 5,504,296 | 965,941 | `libX11.so.6`, `libstdc++.so.6`, `libgcc_s.so.1`, `libc.so.6` |
| EGL | 31,984 | 6,401 | `libGL.so.1`, `libc.so.6` |
| cuda | 1,311,880 | 185,849 | `libstdc++.so.6`, `libgcc_s.so.1`, `libc.so.6` |

This is useful specifically because the approximately 10.1 MiB aggregate file size overstates the directly mapped wrapper footprint: debug/unmapped ELF content is part of those files, whereas the summed loadable segment memory for all eight wrappers is only about 1.69 MiB. GL dominates the measured wrapper memory at about 0.92 MiB; the Vulkan wrapper is about 0.28 MiB.

This is **not** a complete process-memory cost measurement. It does not quantify dirty RSS/PSS, allocator state, loader metadata, generated/JIT state, or dependency closure. In particular GL directly depends on guest `libX11.so.6`, EGL depends on guest `libGL.so.1`, and Vulkan opens X11 manually in `OnInit()`. The result therefore weakens a wrapper-text/data residency objection to generic NODELETE, but it does not establish a 1.69 MiB total runtime cost ceiling.

## Result

The central `add_guest_lib()` location has green compile/link evidence across:

- every current 64-bit shared guest thunk target;
- the special VDSO link mode;
- FEX's real 32-bit guest toolchain on a callback-heavy Wayland wrapper;
- FEX's alternate lld guest-thunk linker mode.

No library-specific or linker-specific NODELETE exception has appeared.

The measured aggregate loadable-memory footprint of the eight current 64-bit wrapper DSOs is about 1.69 MiB before dependency/RSS effects, so the currently measured direct wrapper-residency cost is modest relative to the lifecycle safety benefit under investigation.

All CI/source edits described here are diagnostic work on owned fork/investigation surfaces. No upstream FEX interaction occurred.
