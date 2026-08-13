# Vulkan guest-thunk `NODELETE` design experiment

## TL;DR

The teardown investigation now has a simpler candidate policy to test before implementing generation-aware bridge retirement: make `libvulkan-guest.so` process-resident with the ELF `DF_1_NODELETE` flag.

This directly matches the strongest existing target control: pinning only `libvulkan-guest.so` changes the post-enumeration exit from 139 to 0. A local clang/lld + glibc probe also confirmed that a DSO linked with `-z nodelete` remains mapped and a saved code pointer remains callable after the application's normal `dlclose()`.

The canonical owned-fork experiment is:

- repository: `teamleaderleo/FEX`
- base: FEX-2608 `e869aa644a16e4332cdc15c1ea0b4d13d482385d`
- branch: `diagnostic/vulkan-elf-nodelete-clean`
- commit: `5982a38f1a8e6fcd8aadd2e58e033223c865714f`
- diff: one file, three added lines, zero deletions
- product change: `target_link_options(vulkan-guest PRIVATE "LINKER:-z,nodelete")`
- execution state: written and source-reviewed; target Fedora/FEX execution remains pending because the target VM is outside the current attached runtime

An earlier `diagnostic/vulkan-elf-nodelete` branch accidentally dropped unrelated CMake lines during a full-file connector write. It is discarded provenance. The `-clean` branch was recreated directly from FEX-2608 and verified against the base before being retained.

## Why try this before a larger lifecycle implementation?

The defect class is a lifetime mismatch: FEX stores executable bridges that contain guest addresses from a thunk DSO, while the guest dynamic loader is still allowed to unmap that DSO.

There are two valid ways to make that relationship safe:

1. preserve real unload semantics by revoking every bridge, invalidating translated paths, draining already-selected executions, and only then unmapping the DSO;
2. declare the bridge-owning thunk image process-resident so its executable addresses never become invalid during the process.

The first option is more general. The second option is dramatically smaller.

For Vulkan, residency deserves a direct product experiment because:

- the existing guest-thunk pinning control already repairs the real reproducer;
- Vulkan guest thunk code publishes dynamic-PFN `CallHostFunction` targets into process-owned FEX CustomIR state;
- Vulkan initialization also publishes callback-unpacker addresses into host-owned trampoline state;
- keeping the guest thunk resident protects both classes without requiring the final late caller to be identified first;
- ELF `NODELETE` removes the pre-unmap race entirely because the executable bytes remain present.

## Local ELF `NODELETE` probe

A standalone test DSO was linked with clang/lld using:

```text
-fuse-ld=lld -Wl,-z,nodelete
```

`readelf -d` reported a `FLAGS_1` entry containing `NODELETE`.

The test program then loaded the DSO normally, saved a function pointer, called `dlclose()`, checked `/proc/self/maps`, and called the saved function pointer again.

Observed behavior:

```text
mapping remains after dlclose
saved function remains callable
DSO finalization occurs at process exit
```

Separate local probes produced the same residency behavior by promoting an already-loaded DSO with `RTLD_NOLOAD | RTLD_NODELETE`, including lookup by ELF SONAME and promotion from a DSO constructor. The link-time flag is preferable for the Vulkan experiment because it expresses the lifetime policy directly in the generated guest thunk and requires no constructor-time loader trick.

## What this experiment can prove

If the target Vulkan run with the `-clean` branch:

```text
enumerates llvmpipe
calls the application's ordinary Vulkan dlclose path
keeps libvulkan-guest.so mapped
exits 0
```

then process-resident Vulkan guest thunk code is sufficient to contain the observed failure in source, rather than only through an external preload.

A Venus rerun should then confirm that the same policy preserves the accelerated path.

## What it cannot prove

A passing `NODELETE` result does not erase stale bridge metadata. It makes stale executable destinations remain valid.

Therefore it does not provide full unload/reload semantics. The policy retains code and associated static/TLS state until process exit, and DSO finalization is deferred accordingly.

That can be a legitimate contract for a generated graphics thunk, but it should be chosen explicitly rather than described as generic bridge cleanup.

## Decision tree

### If generated Vulkan thunk code may be process-resident

Prefer the small `DF_1_NODELETE` policy and test its compatibility boundaries:

- normal llvmpipe teardown;
- Venus teardown;
- repeated Vulkan `dlopen` / `dlclose` / reopen;
- stable behavior of dynamic PFNs across repeated logical opens;
- expected destructor/finalization timing;
- retained mapping/memory cost;
- process exit;
- existing pinned-thunk, no-op-`dlclose`, and bogus-preload controls.

If those pass, generation-aware retirement may be unnecessary for Vulkan.

### If FEX requires true guest-thunk unload/reload

`NODELETE` is only a containment control. The implementation needs explicit load ownership:

```text
load generation G
  -> register PFN and callback bridges under G
  -> begin unload / mark G draining
  -> block new bridge acquisition
  -> revoke or rebind bridges
  -> invalidate translated paths keyed by native entrypoints
  -> drain executions that already selected G
  -> unmap guest thunk
  -> reclaim metadata
```

A narrower pre-unmap experiment that removes CustomIR entries whose captured guest targets fall in the retiring thunk range remains useful for proving the dynamic-PFN mechanism, but range matching alone is too weak for a final reload design because of address reuse, aliases, shared native PFNs, callbacks, and concurrent execution.

## Current recommendation

Test `diagnostic/vulkan-elf-nodelete-clean` first.

This is a contract test as much as a crash test. If Vulkan works cleanly with normal guest `dlclose()` while the generated guest thunk remains resident, the next question is whether FEX actually needs that thunk's physical unload semantics. Only pay for generation tokens, bridge rebinding, and execution draining if the answer is yes.

The broader lifecycle reasoning remains in [`../../notes/processes/fex-thunk-bridges-must-retire-before-guest-dso-unmap.md`](../../notes/processes/fex-thunk-bridges-must-retire-before-guest-dso-unmap.md), and the exact failing teardown chronology remains in [`TEARDOWN_CHRONOLOGY.md`](./TEARDOWN_CHRONOLOGY.md).