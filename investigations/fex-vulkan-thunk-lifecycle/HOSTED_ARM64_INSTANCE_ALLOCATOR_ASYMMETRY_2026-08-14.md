# Hosted ARM64 instance allocator asymmetry — 2026-08-14

Status: demonstrated runtime finding on exact reviewed FEX product source.

Product revision: `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX carrier commit: `3d0b0f2103deff80d51f1cfa532aee994eca14a4`.
Workflow run: `31769093369`.
Runner: GitHub hosted `ubuntu-24.04-arm`.
Driver: Lavapipe.
Fieldwork probe revision: `30efcd54d84ad5f18411986015a232597a0025a3`.

The workflow verified that the carrier had no product-source delta under `ThunkLibs`, `FEXCore`, or `Source` relative to `71afe476751deac24adabd1adb575fd2337b6e0a` before building FEX.

## Probe contract

The probe passes the **same valid `VkAllocationCallbacks` object** to both `vkCreateInstance` and `vkDestroyInstance`.

This is not an intentional create/destroy mismatch. The guest application follows Vulkan's allocator-pairing rule at its API boundary.

The x86-64 callback entrypoints include the retained cross-ISA discriminator used elsewhere in this investigation. A native ARM call into the guest x86 callback therefore faults with SIGILL before the guest callback body can execute.

## Native ARM64 control

Observed:

```text
CASE allocator create_allocator=yes destroy_allocator=yes
MARK create-enter
MARK create-return result=0 instance=<non-null> alloc=165 realloc=4 free=141
MARK destroy-enter
MARK destroy-return alloc=165 realloc=4 free=161 free_delta=20
PASS allocator native-valid create/destroy callbacks observed
```

Exit:

```text
native=0
```

This proves the probe is a valid allocator pairing and that the native implementation actually uses the callbacks on both creation and destruction.

## Exact FEX result

Observed:

```text
CASE allocator create_allocator=yes destroy_allocator=yes
MARK create-enter
MARK create-return result=0 instance=<non-null> alloc=0 realloc=0 free=0
MARK destroy-enter
```

There is no `MARK destroy-return`.

The process terminates:

```text
fex=132
Illegal instruction
```

## Interpretation

The result matches the reviewed source asymmetry exactly:

1. FEX's custom `vkCreateInstance` ignores the guest allocator and calls native `vkCreateInstance(..., nullptr, ...)`.
2. Creation therefore succeeds with zero guest allocator callbacks.
3. `vkDestroyInstance` is an ordinary generated thunk rather than a matching callback-aware custom wrapper.
4. The same guest allocator passed by the application reaches the native destruction path without cross-ISA callback mediation.
5. Native destruction attempts to invoke a guest allocator callback and enters the x86 callback pointer as ARM64 code, producing SIGILL before the guest callback body or `MARK destroy-return`.

This promotes the allocator create/destroy asymmetry from a source-level concern to a direct runtime finding.

## Relationship to the earlier `vkCreateBuffer` allocator result

The earlier hosted ARM64 allocator run demonstrated a **generic raw-forwarding** failure: `vkCreateBuffer` with NULL allocator returns normally, while a valid guest allocator causes SIGILL before `vkCreateBuffer` returns.

This run demonstrates a separate but related **policy asymmetry**: a custom create wrapper suppresses the allocator, while the matching generic destroy path later exposes the guest callbacks.

Together they show that the Vulkan thunk cannot be repaired by special-casing one command. `VkAllocationCallbacks` needs a coherent cross-command policy: callback mediation, consistent supported suppression where semantically valid, or explicit rejection of unsupported non-NULL allocators before native code can invoke guest pointers.

## Evidence boundary

Demonstrated here: exact current reviewed product source, native-valid instance allocator pairing, FEX create succeeds with zero guest callbacks, and FEX destroy faults SIGILL before return.

Not demonstrated by this run: every other allocator-bearing Vulkan command or every create/destroy family has the same runtime behavior. Those remain source-scoped until individually executed.
