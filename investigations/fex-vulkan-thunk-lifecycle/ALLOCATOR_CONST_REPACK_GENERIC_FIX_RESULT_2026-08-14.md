# Generic const-preserving repack fix result — 2026-08-14

## Result

The generic const-preserving ThunkGen repair passed both its focused generator regression and the Vulkan allocator runtime matrix.

Owned-fork run:

[`31787054756`](https://redirect.github.com/teamleaderleo/FEX/actions/runs/31787054756)

Exact FEX product source under the Vulkan runtime carrier:

`71afe476751deac24adabd1adb575fd2337b6e0a`

Artifact:

- id: `9214057784`
- name: `const-repack-fix-31787054756`
- digest: `sha256:d65cff9b00af30cae443111d6f8d38487adcf9405cc1ff37d433e160f8439891`

## Generic fix direction

The failure described in `ALLOCATOR_CONST_REPACK_AUDIT.md` comes from generator emission stripping pointee constness before instantiating `repack_wrapper`.

The successful candidate changes generated repack-wrapper emission so a source parameter such as:

```cpp
const A *
```

retains that constness in the wrapper type rather than becoming an `A *` wrapper. `repack_wrapper` may still use mutable temporary host storage internally, but its existing exit-copyback policy can now see that the original API input points to const data and skip automatic writeback.

This is a generic generator correction, not a Vulkan-specific no-writeback exception.

## Focused ThunkGen regression

The candidate adds a `StructRepacking` regression for a pointer-to-const repackable structure and verifies the generated wrapper preserves the source constness.

The focused test completed successfully:

```text
All tests passed (28 assertions in 1 test case)
```

## Vulkan runtime matrix

The same build then runs two independent allocation-callback lifetime probes:

```text
native_buffer=0
fex_buffer=0
native_event=0
fex_event=0
```

The FEX buffer path reaches the guest free callback and returns from destroy:

```text
CB_FREE_ENTER
CB_FREE_RETURN
API_DESTROY_RETURN
```

The independent `VkEvent` path likewise reaches:

```text
EVENT_FREE_ENTER
EVENT_FREE_RETURN
EVENT_DESTROY_RETURN
PASS event allocator lifetime
```

These are the same cross-call lifetimes that failed when the generated repack wrapper wrote its temporary host allocator back over the application-owned `const VkAllocationCallbacks` object.

## Interpretation

This closes the two pending validation gates in `ALLOCATOR_CONST_REPACK_AUDIT.md`:

1. the const-preserving generator change passes a focused non-Vulkan ThunkGen regression;
2. the generic change independently makes both Vulkan buffer and event allocation-callback lifetimes pass without the Vulkan-only custom-exit suppression control.

Therefore the preferred diagnosis is now supported both generically and at runtime:

> generated repack-wrapper emission must preserve the public API's pointee constness so input-only structures are not automatically copied back on scope exit.

The same generator/`repack_wrapper` constness mismatch is present in the later reviewed FEX source `f3ab82a73fb48271ee12a882c98bc5d823a2b4d1`, so the mechanism is not limited to the historical allocator carrier. A separate current-main runtime rerun is optional confirmation rather than a prerequisite for the causal classification.

## Boundary

This result repairs the allocator candidate's caller-input corruption. It does not by itself solve every `VkAllocationCallbacks` policy question: the allocator callbacks still need proper cross-ISA mediation, custom Vulkan wrappers that currently discard `pAllocator` need separate treatment, and broader callback lifetime semantics remain governed by the resident-bridge / generation-lifetime work.

This is fork-local research evidence and diagnostic implementation work, not upstream-ready FEX contribution code.