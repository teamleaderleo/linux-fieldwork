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

The focused hosted lane stages exactly that filename, so the expected host-thunk path convention is satisfied.

FEX's Linux x86 decoder reserves two-byte opcode `0x0f 0x3f` for `ThunkOp`. `OpDispatchBuilder::ThunkOp` reads the SHA-256 bytes immediately after the opcode and emits a thunk IR operation using the guest argument pointer.

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
6. records whether that guest handler receives the failure.

## Trace run 1 — hosted runner Clang discovery failure

```text
Actions run: 31733051239
job: 94557917476
CI commit: 586acf0405e7c874070b8c1c3864e1c104f670e4
artifact: 9194030381
artifact zip SHA-256: 1040216d003d9d3ac9b4a3e36f81f02482c261822f55c501b6a099eababcae6f
```

The run stopped in host CMake configure before product compilation. The newer hosted image exposed a stale Clang 17 CMake package whose imported `clangBasic` target pointed at a deleted file:

```text
/usr/lib/llvm-17/lib/libclangBasic.a
```

The apt transaction installed the LLVM/Clang 18 development tree. The failure belongs to runner-image/tool discovery.

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

## Trace run 2 — guest handler does not receive SIGILL

```text
Actions run: 31733412988
job: 94559124732
CI commit: a8910a6bbfb691b8775a4bc8a5ab9da6e7d728fe
source under test: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9194264601
artifact zip SHA-256: 721b04e3e8ceafd017fc827af0aaaec3b7926d24557552c5942211ab3742e9a7
```

This run completed the full focused build and execution recipe successfully as a diagnostic job. The guest probe process itself still ended with exit `132`.

The generated guest Vulkan thunk disassembly contains:

```text
00000000000144f0 <fexthunks_fex_loadlib>:
   144f0: 0f 3f
```

followed by the expected built-in `fex:loadlib` hash bytes. Many generated Vulkan API thunk entries likewise begin with `0f 3f`.

The x86 probe installed a guest SIGILL handler before `dlopen("libvulkan.so.1")` and printed:

```text
TRACE_BEFORE_DLOPEN
```

The process then terminated as:

```text
Illegal instruction (core dumped)
exit 132
```

Crucially, none of the handler markers (`SIGILL_CAUGHT`, guest RIP, or guest maps) appeared.

Interpretation boundary: the failure is observed as a SIGILL terminating the host FEX process while the guest is inside Vulkan `dlopen`; the installed guest SIGILL handler does not receive it. This makes an ordinary guest SIGILL at the generated `0f 3f` site a poor fit for the observed behavior. The next useful receipt is a host-side signal address plus mmap/open history so the fault can be assigned to FEX JIT/runtime code, the host Vulkan thunk, or another host mapping.

## Next discriminator

Run the same exact build/rootfs/probe under a host signal tracer and record:

- SIGILL `si_addr`;
- host file mappings/opened DSOs around that address;
- any immediately preceding host library load activity.

Keep the callback-routing candidate out of this lane until the Vulkan guest library itself loads successfully.
