# Why this investigation went through FEX, Vulkan, and GDB

## In simple words

The original goal was not to make `vulkaninfo` work. The goal was to run Battle Brothers, a Windows x86-64 game, on an Apple M5 without immediately falling back to a conventional Windows VM or commercial compatibility layer.

That requires several independently risky translations:

```text
Battle Brothers (Windows x86-64)
        ↓
Wine / Proton                 Windows APIs → Linux APIs
        ↓
FEX                           x86-64 CPU → ARM64 CPU
        ↓
Fedora ARM64 guest
        ↓
Vulkan / Mesa Venus
        ↓
virtio-gpu / krunkit
        ↓
Apple M5 GPU
```

The investigation deliberately tested this stack from the bottom upward. `vulkaninfo` was chosen because it removes Wine, Steam, Proton, DXVK, the game, and mods from the experiment while still exercising the x86-64 → FEX → native ARM64 Vulkan → GPU boundary that a performant gaming stack may depend on.

The result was not merely "Vulkan eventually worked." The reduced probe exposed two separate FEX failures that would have been extremely difficult to attribute if they first appeared as a game-launch failure.

## Why FEX was in the stack

The Apple M5 is ARM64. Battle Brothers and most Windows/Linux desktop gaming binaries and compatibility tooling are x86-64.

Wine translates Windows APIs; it does not by itself turn x86-64 machine code into ARM64 machine code. FEX provides that CPU-architecture translation layer:

```text
x86-64 guest instructions
        ↓
FEX dynamic translation
        ↓
ARM64 host instructions
```

The intended high-level composition is therefore:

```text
Windows x86-64 application
        ↓ Wine / Proton
Linux-facing x86-64 process
        ↓ FEX
ARM64 Linux userspace
```

Alternatives could replace this layer — for example whole-system x86 emulation, an ARM Windows VM with its own x86 emulation, Rosetta-backed Linux virtualization where available, or a macOS-native Wine/Game Porting Toolkit/CrossOver path — but each changes the performance, inspectability, GPU, packaging, or product constraints. FEX was attractive because it runs x86-64 Linux userspace on ARM64 and is inspectable and rebuildable when a boundary fails.

## Why Vulkan mattered

A game needs both CPU execution and a path to the GPU. Vulkan is a low-level graphics API used directly by applications and indirectly by major compatibility layers.

Several plausible gaming paths can converge on Vulkan:

```text
Windows Direct3D
        ↓ DXVK
Vulkan
```

or, for OpenGL through Mesa Zink:

```text
OpenGL
        ↓ Zink
Vulkan
```

Wine can also use OpenGL-oriented paths such as wined3d, and software rendering is possible, so Vulkan is not the only theoretical route. But a working accelerated Vulkan boundary is strategically valuable because it can support high-performance translation paths and because it isolates the GPU stack cleanly.

The diagnostic question was therefore:

> Can an ordinary x86-64 Vulkan program, running through FEX, enumerate and use the accelerated Vulkan device exposed to the ARM64 guest?

`vulkaninfo` is a strong probe for that question because it exercises Vulkan instance creation, dynamic function lookup, callbacks, device enumeration, and teardown without adding Wine or a game engine.

## Bottom-up validation

The stack was tested in layers rather than launching the complete game immediately.

### 1. Native ARM64 Vulkan

Native Fedora ARM64 `vulkaninfo` enumerated:

```text
deviceName = Virtio-GPU Venus (Apple M5)
driverName = venus
```

This established that the lower GPU path already worked:

```text
Apple M5
↑ krunkit / virtio-gpu
↑ Venus
↑ native ARM64 Vulkan
```

A later x86 failure therefore did not, by itself, implicate the Apple GPU, krunkit, or Venus.

### 2. x86-64 Vulkan through FEX

The next probe inserted only the foreign-architecture boundary:

```text
x86-64 vulkaninfo
        ↓
FEX
        ↓
FEX Vulkan guest/host thunks
        ↓
native ARM64 Vulkan
        ↓
Venus
```

This failed with SIGILL on pristine FEX. That narrowed the failure to FEX-side execution/thunking rather than the already-working native GPU stack.

## What a Vulkan thunk is doing

An x86-64 application cannot directly call an arbitrary ARM64 library function pointer. The two sides differ in instruction set and ABI, and callbacks make the direction bidirectional.

FEX's Vulkan thunk layer bridges the boundary approximately as:

```text
x86 Vulkan call
    ↓
guest thunk
    ↓ pack / translate arguments
FEX boundary
    ↓
host thunk
    ↓
native ARM64 Vulkan function
```

Callbacks are more dangerous:

```text
x86 application
    ↓ calls ARM-side Vulkan
native ARM Vulkan
    ↓ calls application callback
x86 callback target
```

A raw guest callback address cannot simply be executed by native ARM code. FEX therefore contains custom callback handling for some Vulkan entrypoints.

The first observed defect was in exactly this class: FEX already had a custom `vkCreateDebugReportCallbackEXT` implementation that substitutes a native dummy callback, but the dynamic custom-function lookup did not select it when `vulkaninfo` obtained the function through `vkGetInstanceProcAddr()`. The observed consequence was native execution reaching guest x86 code and terminating with SIGILL. Routing dynamic lookup to the existing custom implementation removed that original SIGILL.

The detailed evidence remains in `README.md` and `EVIDENCE.md`; this file records why that reduced Vulkan boundary was tested in the first place.

## Why the second crash did not invalidate the first result

After the callback-routing change, `vulkaninfo` advanced much farther:

```text
before
startup → dynamic debug callback → SIGILL

candidate
startup → callback succeeds → Vulkan enumeration succeeds → teardown → SIGSEGV / exit 139
```

A new later failure is evidence that the earlier boundary was crossed, not evidence that the earlier fix did nothing. Treating both crashes as one "Vulkan failure" would have hidden two distinct mechanisms.

The second failure was eventually localized to guest Vulkan thunk lifetime/unload behavior strongly enough that keeping `libvulkan-guest.so` loaded changed the result from exit 139 to exit 0. That remains a separate source-level investigation.

## Why GDB was necessary

Once execution crossed architecture translation, an ordinary Linux signal was ambiguous. A SIGSEGV could have belonged to:

- native Mesa or Venus;
- the ARM64 Vulkan loader;
- a FEX host thunk;
- a FEX guest thunk;
- FEX's JIT or signal machinery;
- translated x86 guest code;
- a callback;
- a stale function pointer or unloaded mapping.

GDB let the investigation separate **host ARM64 state** from **guest x86 state** and ask questions such as:

```text
Where is native ARM execution stopped?
What signal is FEX handling?
What guest RIP did FEX record?
What x86 trap/error code was synthesized?
Is the guest address still mapped?
Which DSO or generated thunk used to own that range?
```

One especially important correction came from this approach. The final native instruction appeared to be a deliberate null dereference:

```asm
mov w1, #0
ldr x1, [x1]
```

Source inspection showed that FEX intentionally emits this sequence in its `GuestSignal_SIGSEGV` trampoline to synthesize a guest SIGSEGV. The native `ldr [0]` was therefore not itself the original defect. FEX's recorded guest fault state then showed an x86 instruction-fetch page fault, which redirected the investigation toward guest code lifetime and mappings.

Without GDB plus source inspection, it would have been easy to misattribute the failure to a native null dereference in Mesa/FEX or to report the wrong owner entirely.

## Why llvmpipe was useful

Mesa's llvmpipe is a software Vulkan implementation. It removes the accelerated Venus/virtio/Apple-GPU path from the experiment while preserving the Vulkan/FEX interface.

The teardown failure also reproduced with llvmpipe:

```text
x86 vulkaninfo
↓ FEX Vulkan thunking
↓ llvmpipe
→ same late exit 139
```

That negative control showed that Venus, virtio-gpu, krunkit, and the Apple GPU were not required for the second failure. The likely owner moved upward toward FEX Vulkan thunk lifecycle.

## Why the preload controls mattered

The second failure became compelling only after differential controls separated a specific lifetime condition from generic environment changes.

Observed matrix:

```text
normal post-callback-fix run        → exit 139
bogus LD_PRELOAD path               → exit 139
x86 preload overriding dlclose      → exit 0
preload only libvulkan-guest.so     → exit 0
same pinned-thunk control on Venus  → exit 0, Apple M5 enumerated
```

The bogus preload is important because it weakens the alternative explanation that merely changing `LD_PRELOAD` or loader diagnostics caused success. Pinning only the Vulkan guest thunk is narrower still: the successful result tracks whether that thunk remains loaded.

This is strong localization evidence, but it is deliberately not described as a complete source fix. The exact FEX invalidation/lifetime owner is the subject of the separate unload review lane.

## OpenGL and Zink are a separate branch

Vulkan working does not automatically mean every graphics API is solved.

Mesa Zink can implement OpenGL on top of Vulkan:

```text
OpenGL
 ↓
Zink
 ↓
Vulkan
 ↓
Venus
```

That would be attractive for Wine/game paths that need OpenGL. In this VM, however, Zink currently refuses the Venus device because the required robustness capability reports `nullDescriptor=false`.

This is a separate compatibility boundary. It does not contradict the demonstrated x86 Vulkan result, and it should not be folded into either FEX Vulkan defect without new evidence.

## Other plausible routes

The chosen route was not the only possible way to pursue the original game goal.

### Whole-system x86 emulation

An x86-64 VM under QEMU could remove the FEX userspace-translation boundary, but CPU performance and accelerated GPU integration become different problems. It also makes the system less directly comparable to the native ARM64/Venus path already available through krunkit.

### ARM Windows VM with x86/x64 application emulation

A Windows-on-ARM VM could rely on Microsoft's compatibility layer. This is operationally conventional but moves control and observability away from the Linux/FEX stack and may require commercial virtualization products.

### CrossOver or other macOS Wine distributions

These may be easier if the sole goal is launching a Windows game. They intentionally hide or solve much of the compatibility stack being investigated here. They remain pragmatic fallback options, but would not answer whether the local Linux/FEX/Venus route is viable.

### Apple's Game Porting Toolkit / macOS-native compatibility stack

A macOS-native path can translate Windows graphics toward Metal and avoids the Linux VM GPU boundary. Again, this is a materially different architecture rather than a direct substitute for debugging the current stack.

### Rosetta-backed Linux virtualization

Where the virtualization stack supports it, Rosetta can translate x86-64 Linux binaries in an ARM Linux VM and could replace FEX for the CPU-translation role. Its availability, integration with the chosen VM backend, packaging behavior, and interaction with the graphics path would need separate validation.

### Software rendering

llvmpipe can provide a correctness fallback without accelerated GPU access. It is useful diagnostically but is unlikely to be the desired final gaming path because rendering work moves to the CPU.

### Wine OpenGL / wined3d path

Wine can use OpenGL-oriented translation instead of Vulkan-oriented paths such as DXVK. In the current environment, accelerated OpenGL through Zink has its own `nullDescriptor` blocker. Software OpenGL remains possible as a diagnostic fallback.

## What this detour established for the original game goal

Before this investigation, the following path was speculative:

```text
x86-64 process
↓ FEX
accelerated Vulkan
↓ Venus
Apple M5
```

It has now been executed successfully under the pinned-thunk control:

```text
deviceName = Virtio-GPU Venus (Apple M5)
driverName = venus
exit = 0
```

That removes a large uncertainty from the eventual Wine/Battle Brothers stack.

Current stack status, deliberately separating proven and unresolved layers:

```text
✓ ARM64 Fedora VM on Apple M5
✓ native Venus Vulkan in guest
✓ x86-64 execution through FEX
✓ x86-64 Vulkan calls through FEX reach Venus
✓ pinned-thunk control exits cleanly
? source-level repair for FEX thunk unload lifecycle
? writable x86-64 userspace for Wine
? Wine prefix / Windows executable validation
? game graphics translation choice
? accelerated OpenGL if required
? presentation/windowing from the headless VM
? Battle Brothers itself
? mod stack
```

## Method lesson

The high-level debugging sequence was intentional:

```text
native GPU probe
→ foreign-architecture GPU probe
→ reduce first crash
→ inspect owning source
→ classify host vs guest signal state
→ add a negative control
→ perturb one lifetime condition
→ rerun on software backend
→ rerun on real accelerated backend
```

Launching Steam, Proton, Wine, the game, and mods at the beginning would have produced a much larger failure surface:

```text
Battle Brothers
Steam
Proton / Wine
DXVK or wined3d
FEX
Vulkan thunking
Mesa
Venus
virtio-gpu
krunkit
macOS
Apple GPU
```

A generic "game crashed" at that level would not identify the owner. The reduced `vulkaninfo` path was valuable precisely because it removed most of those layers while preserving the compatibility boundary under question.

## What could have been done better

The main process improvement is evidence capture, not a different technical direction. Once the first pristine FEX SIGILL became reproducible, the investigation should have moved into a durable fieldwork record earlier rather than allowing chat to function as the primary notebook for so long.

The repository is now the recovery source of truth. Future work should keep the same bottom-up, discriminating-probe style while writing checkpoints as soon as a new failure becomes stable.

## Evidence boundary

This note explains the architecture and why the probes were chosen. It does not expand the technical claims beyond the executed investigation.

In particular:

- the callback-routing finding is demonstrated only for the tested FEX/Vulkan path and still deserves independent regression-design review;
- the unload/lifetime mechanism is strongly localized but its exact source owner is not yet fully proved;
- Vulkan success does not establish working Wine, DXVK, OpenGL, window presentation, Battle Brothers, or mods;
- llvmpipe proves a software-renderer control, not acceptable game performance;
- alternative stacks listed above are architectural options, not benchmarked recommendations from this investigation;
- no upstream interaction is authorized or performed by this record.
