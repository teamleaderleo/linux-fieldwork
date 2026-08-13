# Why the hosted ARM64 lane exists

This lane exists for one practical reason: move repetitive FEX/Vulkan reproduction work off the Apple M5 machine and onto disposable GitHub-hosted ARM64 runners.

The M5/Venus machine is valuable because it is the hardware path we ultimately care about. It is a poor place to spend human time repeatedly discovering build dependencies, rootfs mistakes, thunk bitness mistakes, probe compiler warnings, or other CI/setup failures.

The hosted lane answers a narrower question first: can a clean ARM64 machine build the exact FEX revision, build the Vulkan thunk pair, run an amd64 userspace through FEX, and reach the same callback boundary with software Vulkan? If yes, most iteration can happen automatically. The Apple/Venus test becomes a final hardware confirmation.

## What the lane has proved

As of Actions run `31730826384` on `teamleaderleo/FEX`:

- GitHub `ubuntu-24.04-arm` can build exact FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`.
- The focused runtime set includes `FEXServer` plus `vulkan-host-64`; this produces working FEX runtime pieces and the explicit 64-bit Vulkan host thunk.
- A standalone 64-bit `vulkan-guest` thunk builds with the x86-64 cross toolchain.
- Native ARM64 Lavapipe works and the native callback control succeeds.
- An amd64 Ubuntu 24.04 rootfs can be exported from an OCI image without executing amd64 code in Docker.
- Static x86-64 execution under FEX succeeds.
- Dynamically linked x86-64 execution under FEX succeeds.

The clean phase matrix was:

```text
static x86-64 under FEX      = 0
dynamic x86-64 under FEX     = 0
Vulkan dlopen                = 132
direct Vulkan callback       = 132
GIPA callback baseline       = 132
GIPA callback candidate      = 132
```

The current first failing boundary is therefore the generated Vulkan guest thunk load, before the callback-routing discriminator itself.

## Why the earlier CI churn was useful

The preceding runs removed three false owners from the experiment:

1. A broad workflow selected a 32-bit host Vulkan thunk for a 64-bit guest via a loose `find | head -1`.
2. The first focused runtime build omitted the separate `FEXServer` target, so every guest case exited before guest code.
3. A phase helper compiled with `-Werror` ignored `write(2, ...)`, stopping a run before execution.

Those are harness findings. Recording them keeps future failures from being misreported as FEX Vulkan behavior.

## Current goal

The next hosted experiment should explain the SIGILL at the first `dlopen("libvulkan.so.1")` of the generated guest thunk. FEX's thunk documentation says replacing the guest native library with the generated guest thunk is a normal usage model, and the guest thunk constructor immediately performs the special `fex:loadlib` transition. The useful next discriminator is therefore around that load transition and matching host-thunk discovery.

Once Vulkan library loading succeeds, rerun the direct callback, GIPA baseline, and one-line diagnostic routing candidate. That is the Finding A A/B we actually wanted from hosted CI.

## Human-machine division

Hosted ARM64 should own build, rootfs, x86 runtime, software Vulkan, and small callback A/B iteration.

Apple M5/Venus should own the final hardware-specific confirmation after the hosted path reaches the callback cleanly.
