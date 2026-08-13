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

`ThunkHandler_impl::LoadLib()` opens the host thunk, resolves its export table, initializes it, and registers every exported thunk hash before returning to the guest constructor. `LookupThunk()` returns the registered host function for a matching hash and `nullptr` for an unknown hash.

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

None of the handler markers (`SIGILL_CAUGHT`, guest RIP, or guest maps) appeared.

Interpretation boundary: the failure is observed as a SIGILL terminating the host FEX process while the guest is inside Vulkan `dlopen`; the installed guest SIGILL handler does not receive it. An ordinary guest SIGILL at the generated `0f 3f` site fits the receipt poorly.

The trace workflow accidentally omitted `mesa-vulkan-drivers` and `vulkan-tools`. The earlier clean run `31730826384` included both plus host `libvulkan1:arm64` and produced the same Vulkan-load exit `132`, so host Vulkan package presence does not explain the original failure.

## Narrowed constructor-time candidate: missing guest X11 helpers

The Vulkan guest thunk does more work before its `dlopen()` constructor returns. Its `OnInit()` executes:

```text
dlopen("libX11.so.6", RTLD_LAZY)
dlsym(..., "XSync")
fexfn_pack_Vulkan_SetGuestXSync(...)
dlsym(..., "XGetVisualInfo")
fexfn_pack_Vulkan_SetGuestXGetVisualInfo(...)
dlsym(..., "XDisplayString")
fexfn_pack_Vulkan_SetGuestXDisplayString(...)
```

The focused amd64 runtime is a bare `ubuntu:24.04` filesystem. The workflow adds the generated Vulkan guest thunk, guest `libstdc++`, and guest `libgcc_s`; it does not add x86-64 X11 runtime libraries.

If guest `libX11.so.6` is absent, those helper lookups can produce null guest function addresses. On the host side each `Vulkan_SetGuestX*` implementation immediately calls `MakeHostTrampolineForGuestFunctionAt()` with that guest target. The trampoline path explicitly rejects a null guest target (`Tried to create host-trampoline to null pointer guest function`).

This candidate matches the observed phase boundary closely:

```text
plain dynamic x86: succeeds
enter Vulkan dlopen: succeeds far enough to run constructor
constructor X11-helper registration: host-side failure candidate
guest SIGILL handler: never receives signal
```

It also explains why the earlier fuller installed-thunk/rootfs experiments could get farther than the minimal hosted rootfs.

This remains a candidate until an A/B supplies non-null guest X11 helper addresses and observes whether `dlopen("libvulkan.so.1")` returns.

## Next discriminator

Keep exact FEX source, exact host thunk, bare rootfs, and the same x86 loader probe. Add only an x86-64 `libX11.so.6` diagnostic stub exporting:

```text
XSync
XGetVisualInfo
XDisplayString
```

The functions only need stable non-null guest addresses for this load discriminator; the headless callback probe does not exercise X11 presentation.

If Vulkan `dlopen` changes from `132` to `0`, the minimal-rootfs blocker is guest X11 helper registration. Then restore real guest X11 runtime libraries for the callback A/B.

If it remains `132`, continue inside host-thunk initialization/registration. Keep the callback-routing candidate out of this lane until the Vulkan guest library itself loads successfully.
