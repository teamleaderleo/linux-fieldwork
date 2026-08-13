# Hosted ARM64 Vulkan guest-load trace

## Why this lane exists

The clean hosted Finding A run proved that a GitHub ARM64 runner can build FEX, build the focused Vulkan host/guest thunks, create an amd64 Ubuntu rootfs, and run ordinary static and dynamically linked x86-64 binaries under FEX. Its first failing checkpoint was the first `dlopen("libvulkan.so.1")` of the generated Vulkan guest thunk, which exited 132 / SIGILL before the callback-routing A/B could begin.

This trace lane asks one question: where does that SIGILL land?

## Source facts that narrow the question

FEX's thunk documentation explicitly describes replacing a native guest library with the generated guest thunk via a symlink. Directly staging `libvulkan-guest.so` as the guest `libvulkan.so.1` is therefore a supported thunk usage model.

The generated guest thunk contains FEX's special guest-to-host opcode sequence (`0x0f, 0x3f` plus a thunk hash). `LOAD_LIB_INIT(libvulkan, OnInit)` runs during the Vulkan guest library constructor, and its first special transition is `fex:loadlib`.

On the FEX host side, `fex:loadlib` for 64-bit `libvulkan` resolves the matching host library to:

```text
${FEX_THUNKHOSTLIBS}/libvulkan-host.so
```

The focused hosted lane stages exactly that filename, so the expected host-thunk path convention is already satisfied.

## Trace method

The owned-fork branch is:

```text
ci/agent-c-vulkan-load-sigill-20260814
```

The purpose-built workflow builds exact reviewed FEX source:

```text
71afe476751deac24adabd1adb575fd2337b6e0a
```

and then:

1. builds `FEXServer` and `vulkan-host-64`;
2. builds standalone 64-bit `vulkan-guest`;
3. records guest-thunk disassembly around `0f 3f` sites;
4. exports an amd64 Ubuntu 24.04 rootfs;
5. installs an x86-64 SIGILL handler before calling `dlopen("libvulkan.so.1")`;
6. on SIGILL, records `si_addr`, guest RIP when available, and `/proc/self/maps`.

A guest RIP that lands on one of the generated `0f 3f` sites points directly at the thunk transition/recognition boundary. A later RIP moves the first owner farther into host-thunk load or Vulkan guest initialization.

## Trace run 1 — hosted runner Clang discovery failure

```text
Actions run: 31733051239
job: 94557917476
CI commit: 586acf0405e7c874070b8c1c3864e1c104f670e4
artifact: 9194030381
artifact zip SHA-256: 1040216d003d9d3ac9b4a3e36f81f02482c261822f55c501b6a099eababcae6f
```

The run stopped in host CMake configure before product compilation. The newer `ubuntu-24.04-arm` runner image exposed a stale Clang 17 CMake package whose imported `clangBasic` target pointed at a deleted file:

```text
/usr/lib/llvm-17/lib/libclangBasic.a
```

The apt transaction installed the LLVM/Clang 18 development tree. The failure is runner-image/tool-discovery noise, not FEX behavior.

Correction: install and select LLVM/Clang 18 explicitly:

```text
clang-18
lld-18
libclang-18-dev
llvm-18-dev
Clang_DIR=/usr/lib/llvm-18/lib/cmake/clang
LLVM_DIR=/usr/lib/llvm-18/lib/cmake/llvm
CC=clang-18
CXX=clang++-18
```

Corrected owned-fork CI commit:

```text
a8910a6bbfb691b8775a4bc8a5ab9da6e7d728fe
```

Corrected run:

```text
Actions run: 31733412988
```

Status when this note was written: in progress.
