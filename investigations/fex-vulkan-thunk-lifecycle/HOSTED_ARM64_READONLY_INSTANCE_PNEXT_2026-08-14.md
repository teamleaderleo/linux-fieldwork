# Hosted ARM64 read-only instance pNext mutation fault — 2026-08-14

Status: demonstrated runtime finding on exact reviewed FEX product source.

Product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX carrier commit: `f5c32d5f524102128ca76ef21d765c4a0900c1d4`.
Workflow run: `31770241831`.
Job: `94674461075`.
Artifact: `9207921691`, `agent-b-readonly-pnext-31770241831`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Driver: Lavapipe.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `71afe476...` before building FEX.

## Probe contract

The probe places the **root `VkInstanceCreateInfo`** on its own mmap page, initializes a valid `VK_EXT_debug_report` pNext node, then changes only the root page to `PROT_READ` with `mprotect()` before calling `vkCreateInstance`.

The pNext node itself remains ordinary writable process memory. This specifically tests whether the implementation writes through the caller's `const VkInstanceCreateInfo*` root while trying to remove the debug-report node.

The instance enables `VK_EXT_debug_report` and also requests an intentionally missing extension. The expected native result is therefore `VK_ERROR_EXTENSION_NOT_PRESENT`, with the input pNext link unchanged.

No cross-ISA callback invocation is required for this discriminator.

## Native ARM64 control

Observed:

```text
MARK readonly=<read-only page> pnext=<debug-report node>
MARK create-enter
MARK create-return result=-7 instance=(nil) pnext=<same debug-report node> same=1
```

Exit:

```text
native=0
```

This establishes that the read-only caller-owned root is valid input for the loader path and is not modified by native Vulkan.

## Exact FEX result

Observed:

```text
MARK readonly=0x7ffff7ec4000 pnext=0x7fffffffd5c0
MARK create-enter
```

There is no `MARK create-return`.

The process terminates:

```text
fex=139
Segmentation fault
```

## Source match

At the reviewed FEX revision, the custom `vkCreateInstance` implementation walks the caller's pNext chain and, when the next node is `VK_STRUCTURE_TYPE_DEBUG_REPORT_CREATE_INFO_EXT`, executes the equivalent of:

```cpp
const_cast<VkBaseInStructure*>(vk_struct)->pNext = vk_struct->pNext->pNext;
```

For this probe, `vk_struct` is the read-only root `VkInstanceCreateInfo`. The attempted write therefore faults before the native `vkCreateInstance` call can return.

The runtime boundary matches that source behavior exactly.

## Interpretation

This promotes the caller-input mutation concern to a direct runtime correctness failure.

The problem is independent of the raw-callback SIGILL findings:

- native control never needs to invoke the debug-report callback;
- the FEX failure is SIGSEGV, not the x86/ARM64 callback discriminator SIGILL;
- FEX dies before native creation can return because it writes through caller-owned read-only input.

It is also independent of the legal multiple-debug-utils-node candidate failure. Even a one-node debug-report chain is enough to trigger the const-input write.

## Design implication

A repair should build a host-side copied/sanitized pNext chain rather than destructively splicing the guest application's input structures.

That copied-chain design can address three distinct requirements together:

1. preserve the caller's `const` input and support read-only memory;
2. process every legal callback-bearing node without the destructive-loop skip seen with repeated debug-utils nodes;
3. explicitly mediate, suppress, or reject callback-bearing members before native code can receive guest function pointers.

A regression suite should include at least:

- writable one-node debug-report input and post-call structural equality;
- read-only root create-info;
- one debug-utils messenger node;
- two legal adjacent debug-utils messenger nodes;
- callback-bearing nodes separated by unrelated legal pNext structures.

## Evidence boundary

Demonstrated here:

- exact `71afe...` product source;
- native read-only control returns `-7` and preserves pNext;
- FEX enters `vkCreateInstance` and SIGSEGVs before return on the same read-only-root shape.

Not demonstrated here:

- a production-ready copied-chain implementation;
- every callback-bearing Vulkan pNext type;
- this exact probe rerun against upstream current `f3ab82...` (the Vulkan `Host.cpp` source is byte-identical there, but runtime has not yet been repeated).

No upstream write or interaction was performed.
