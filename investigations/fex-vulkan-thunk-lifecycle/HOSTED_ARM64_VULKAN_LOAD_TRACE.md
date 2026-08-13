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

and then builds focused FEX/Vulkan thunks, exports an amd64 Ubuntu rootfs, and runs a small x86 loader probe under FEX.

## Trace run 1 — hosted runner Clang discovery failure

```text
Actions run: 31733051239
job: 94557917476
CI commit: 586acf0405e7c874070b8c1c3864e1c104f670e4
artifact: 9194030381
artifact zip SHA-256: 1040216d003d9d3ac9b4a3e36f81f02482c261822f55c501b6a099eababcae6f
```

The run stopped in host CMake configure before product compilation. The hosted image exposed a stale Clang 17 CMake package whose imported `clangBasic` target pointed at a deleted file:

```text
/usr/lib/llvm-17/lib/libclangBasic.a
```

Correction: select LLVM/Clang 18 explicitly.

## Trace run 2 — host trap during guest Vulkan constructor

```text
Actions run: 31733412988
job: 94559124732
CI commit: a8910a6bbfb691b8775a4bc8a5ab9da6e7d728fe
source under test: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9194264601
artifact zip SHA-256: 721b04e3e8ceafd017fc827af0aaaec3b7926d24557552c5942211ab3742e9a7
```

The generated guest Vulkan thunk disassembly contains:

```text
00000000000144f0 <fexthunks_fex_loadlib>:
   144f0: 0f 3f
```

The x86 probe installed a guest SIGILL handler before `dlopen("libvulkan.so.1")` and printed:

```text
TRACE_BEFORE_DLOPEN
```

The FEX host process then terminated with exit `132`. The guest SIGILL handler never ran.

The earlier clean run `31730826384` included host `mesa-vulkan-drivers`, `vulkan-tools`, and `libvulkan1:arm64` and produced the same Vulkan-load exit `132`, so native host Vulkan package presence did not explain the failure.

## Source cause: guest X11 helper registration

The Vulkan guest thunk does additional constructor work before guest `dlopen()` returns:

```text
dlopen("libX11.so.6", RTLD_LAZY)
dlsym(..., "XSync")
fexfn_pack_Vulkan_SetGuestXSync(...)
dlsym(..., "XGetVisualInfo")
fexfn_pack_Vulkan_SetGuestXGetVisualInfo(...)
dlsym(..., "XDisplayString")
fexfn_pack_Vulkan_SetGuestXDisplayString(...)
```

The minimal amd64 rootfs was a bare `ubuntu:24.04` export plus the generated Vulkan guest thunk, guest `libstdc++`, and guest `libgcc_s`. It did not stage x86-64 X11 runtime libraries.

On the host side each `Vulkan_SetGuestX*` call creates a host-to-guest trampoline. `MakeHostTrampolineForGuestFunction()` asserts that the guest target is nonzero:

```text
Tried to create host-trampoline to null pointer guest function
```

With assertions enabled, FEX's assertion path ends in `FEX_TRAP_EXECUTION`. That produces a host-side illegal-instruction termination, explaining why the guest SIGILL handler never ran.

## Trace run 3 — X11-symbol A/B confirms the minimal-rootfs blocker

```text
Actions run: 31735763551
job: 94566884546
CI commit: bc86e56e25cfadd3480e93f94c840ce9d5a027cb
source under test: 71afe476751deac24adabd1adb575fd2337b6e0a
artifact: 9195164100
artifact zip SHA-256: d1e475bf1e3e359aa239da662d80242dd09aa070317555009307c251610970d4
```

This run restored native Lavapipe packages/control and changed the guest rootfs by adding one diagnostic x86-64 `libX11.so.6` exporting only:

```text
XSync
XGetVisualInfo
XDisplayString
```

The functions are inert; their purpose is only to provide stable non-null guest addresses during the Vulkan guest constructor.

Observed result:

```text
TRACE_BEFORE_DLOPEN
TRACE_AFTER_DLOPEN
exit 0
```

Baseline without guest X11 helpers: `132`.

Diagnostic non-null X11 helpers: `0`.

Conclusion: the hosted Vulkan-load SIGILL was a minimal-rootfs harness failure. The guest Vulkan constructor expected X11 helper symbols, received null guest targets, and FEX's assertion path deliberately trapped on host ARM64. It is not evidence against Vulkan thunk loading or Finding A.

## Consequence for Finding A

The hosted ARM64 lane is now usable through guest Vulkan library loading. For the actual callback-routing A/B, provide real x86-64 X11 runtime libraries or retain the inert diagnostic helpers for a headless callback probe that does not exercise X11 presentation.

The next useful test is the original direct/GIPA callback matrix with this rootfs repair:

```text
direct debug-report callback
GIPA debug-report callback on exact baseline
GIPA debug-report callback after diagnostic host lookup route
```

That is the experiment the hosted lane was created to run.
