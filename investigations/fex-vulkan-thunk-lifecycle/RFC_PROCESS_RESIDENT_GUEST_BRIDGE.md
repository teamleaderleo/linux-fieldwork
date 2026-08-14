# RFC: Process-resident guest bridge for unloadable FEX thunk wrappers

Date: 2026-08-14
Status: research proposal
Scope: owned research surfaces only

## TL;DR

Generate a private resident companion DSO for each lifetime-sensitive thunk family and guest bitness. The companion owns generated executable helpers whose addresses can escape the ordinary guest wrapper. The public wrapper keeps ordinary API entrypoints and may physically unload.

Initial ownership split:

```text
libvulkan-guest.so generation
  ordinary exported API wrappers
  per-load initialization state that does not escape

libfex-vulkan-bridge.so resident companion
  generated CallHostFunction<signature> adapters used by returned native PFNs
  generated CallbackUnpack<signature>::Unpack helpers whose addresses escape
  explicitly declared custom executable helper addresses that escape

independent guest callback target
  owned by the guest mapping/load generation that supplied it
```

This design removes the wrapper-unload race for bridge executable code without requiring JIT/cache lifetime reclamation changes.

## Goal

Preserve physical unload/reload of ordinary guest thunk wrappers while keeping every FEX-created executable helper valid for as long as native/FEX state may retain its address.

## Non-goals for the first implementation

The first resident bridge implementation does not attempt to reclaim resident bridge executable code during process lifetime.

It also does not extend the lifetime of arbitrary guest callback targets supplied by unrelated guest DSOs. Those targets require their own owner/generation contract when native state retains them past guest unload.

Cross-library signature deduplication is deferred until semantic identity has a complete typed definition.

## Proven runtime model

### Vulkan

The strongest current Vulkan prototype derives resident and wrapper output from the same thunkgen-generated guest file.

Observed build identity:

```text
normal guest runtime signatures    = 476
resident bridge runtime signatures = 476
sets identical                     = yes
bridge file size                   = 2,079,504 bytes
wrapper NODELETE                   = no
wrapper NEEDED bridge              = yes
bridge NODELETE                    = yes
```

Observed runtime gates:

```text
retained vkEnumerateInstanceVersion after wrapper unmap -> works
persistent X11 callback path after wrapper unmap         -> works
forced moved wrapper reload                              -> works
old and newly reacquired stable native H                 -> both work
```

A real amd64 Ubuntu `vulkaninfo --summary` also completes under hosted ARM64 FEX with the split bridge. The unsplit and split arms both exit `0`, and the split trace shows many real Vulkan native PFNs linked to resident guest bridge adapters.

See:

- [`GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_PFN_RUNTIME_2026-08-14.md)
- [`GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_BRIDGE_X11_RUNTIME_2026-08-14.md)
- [`GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md`](./GENERATED_VULKAN_SPLIT_MOVED_RELOAD_RUNTIME_2026-08-14.md)
- [`HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md`](./HOSTED_VULKANINFO_SPLIT_BRIDGE_AB_2026-08-14.md)

### GL

An independent generated GL split-bridge experiment demonstrates the same lifetime facts:

```text
old libGL wrapper generation physically unmapped
replacement wrapper generation moved
native H remained bit-identical
resident guest adapter remained mapped
retained and new calls both succeeded
```

This removes Vulkan-specificity from the core bridge ownership argument.

### DRM callback unpacker

A moved-reload DRM server-info experiment establishes the callback-unpacker half:

```text
wrapper-owned unpacker -> 139
resident unpacker      -> 0
```

The actual callback target in that test remains separately owned, which is intentional: the test isolates unpacker lifetime from target lifetime.

## Why residency beats retirement for generated escape helpers

Exact H retirement plus cache invalidation repairs future lookup state. A forced two-thread test proves it cannot revoke a guest target already selected by another thread before unmap.

A resident bridge changes the premise. Once the selected target is a process-lived generated bridge helper, ordinary wrapper unmap no longer invalidates the selected executable address.

Therefore wrapper physical reclamation can remain independent of JIT execution-drain work for this helper class.

## Output ownership rules

Thunkgen should classify generated code according to whether its executable address can escape the wrapper invocation/load generation.

### Wrapper-owned output

Keep in the ordinary guest wrapper:

- exported API wrapper entrypoints;
- synchronous marshalling code whose address never escapes;
- helper state whose lifetime is bounded by the wrapper call/load and carries no externally retained executable address.

### Resident generated output

Emit into the resident companion:

- `CallHostFunction<signature>` adapters selected for native PFNs returned to guest code;
- `CallbackUnpack<signature>::Unpack` used in callbacks that native/FEX state may retain;
- nested callback-member unpacker signatures discovered from typed interface metadata;
- custom executable helper functions explicitly declared as escaping.

### Independently owned callback target

The guest callback function itself remains owned by the guest mapping that contains it.

If native state retains that target after its owner can unload, the runtime needs owner/generation retirement plus an execution-safety policy. Resident unpackers do not erase this boundary.

## Generator integration

The production implementation should emit bridge definitions directly from thunkgen analysis.

The current strongest Vulkan proof uses a post-processing script to split generated C++ output. That proves output ownership is workable while sacrificing typed context too early for production use.

Thunkgen already knows enough to identify several useful classes:

- returned function-pointer signatures;
- ordinary callback parameter signatures;
- layout and parameter annotations.

The DRM nested-callback prototype adds evidence that thunkgen can also classify callbacks inside a structure with explicit member metadata.

## Nested callback members

Current-main `drmHandleEvent` receives `drmEventContext*`, whose callback fields were previously treated as ABI-compatible inert data.

A research `callback_member` annotation generates conversion automatically. The candidate matrix is:

```text
native=0
pristine_reference=132
generated_candidate=0
```

The guest side copies the caller structure and converts only annotated callback fields in a temporary copy. The host side finalizes the typed trampolines before native execution.

See [`DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md`](./DRM_NESTED_CALLBACK_GENERATOR_PROTOTYPE.md).

These member signatures should feed the same resident bridge signature set as direct callback parameters when the callback can outlive the wrapper.

## Retained containing objects

Callable-pointer conversion and containing-object lifetime are independent contracts.

For `drmHandleEvent`, native code consumes the callback-bearing structure synchronously, so a temporary converted copy is sufficient.

For `drmSetServerInfo`, native libdrm retains the supplied containing object and later invokes `load_module` from another call path. A stack or transient repack object would become stale even if every callback unpacker lived in the resident bridge.

The generator therefore needs explicit retained-object metadata when native code keeps a converted object after the thunk returns.

A possible research vocabulary is:

```text
callback_member
retained_input
retained_until<event-or-owner>
```

The final names are an API design choice. The important requirement is preserving the distinction.

## Custom raw-address publication

Vulkan and GL contain internal helpers that publish executable addresses through `uintptr_t`-typed setup functions. Their semantics are opaque to ordinary type analysis.

The production generator should avoid a manually maintained name registry when possible. Prefer explicit typed escape declarations on the relevant internal interface.

The declaration must answer:

```text
which executable address escapes?
which signature does it implement?
which resident owner should contain it?
```

For helper state that retains a non-executable converted object, use separate retained-object metadata.

## Component granularity

### Proposed first implementation

One resident companion per thunk family and bitness.

Examples:

```text
libfex-vulkan-bridge.so
libfex-GL-bridge.so
libfex-cuda-bridge.so
...
```

The exact names are packaging details.

### Why per-library first

FEX has already had a real GL/Vulkan internal-helper symbol collision where loading one thunk family caused another family to resolve the wrong setup helpers. The repair added library-specific helper names.

That history makes early cross-library aggregation a poor default.

Generated special-thunk identity is strongly signature-derived, but host marshalling semantics can also depend on annotations and library-specific setup. Cross-library sharing should wait for a semantic identity audit.

### Later optimization

Once identity is explicit, a shared adapter pool may deduplicate identical resident helpers across thunk families.

That optimization should preserve library-specific exported/internal setup namespaces and should never use signature equality as a substitute for complete generator semantics.

## Link and discovery model

The ordinary wrapper should acquire resident helper addresses without searching the guest rootfs as though the bridge were a public guest ABI.

Preferred properties:

- bridge remains private FEX implementation material;
- wrapper has a deterministic dependency on the bridge;
- deployment follows FEX's private GuestThunks packaging path;
- bridge selection is per guest bitness and the chosen loader-namespace policy;
- no public application-facing ABI is created.

FEX already has private thunk dependency handling that may provide the clean packaging hook. This requires a dedicated implementation proof before the RFC should prescribe one exact loader mechanism.

## Loader namespace policy

This is the largest unresolved design choice.

Whole-wrapper NODELETE experiments demonstrate that NEWLM namespaces are real lifetime domains. A base-namespace-only promotion cannot repair a NEWLM wrapper that publishes generation-owned callback unpackers into persistent host state.

The bridge design needs an explicit answer to one of these models:

### Model A — bridge follows guest loader namespace

Identity includes at least:

```text
guest bitness + thunk family + loader namespace
```

Each namespace gets its own resident companion instance.

Advantages:

- preserves namespace isolation;
- avoids cross-namespace helper-state collision.

Cost:

- resident namespace instances can accumulate;
- namespace lifecycle and bridge reuse need careful definition.

### Model B — bridge is private FEX process state outside guest namespace lifetime

All wrapper generations publish helpers from one private FEX-owned companion for the family/bitness.

Advantages:

- simplest executable lifetime;
- avoids repeated bridge instances.

Cost:

- any library-specific mutable state crossing namespaces must be prohibited, partitioned, or explicitly keyed;
- symbol lookup and callback helper setup must never accidentally conflate namespaces.

The next namespace experiment should choose between these with two simultaneous NEWLM wrapper generations, independent callback/helper state, close/reload cycles, and explicit namespace exhaustion controls.

## 32-bit ABI

The current strongest generated split-bridge runtime proofs are 64-bit.

A 32-bit end-to-end proof should be a generic-design gate because:

- guest pointer width differs;
- thunk ABI details and callback marshalling differ;
- loader mappings are tighter;
- process-resident memory cost is proportionally more important.

The required test should exercise at least one dynamic PFN and one host->guest callback path through a generated resident companion.

## Memory accounting

Bridge file size is not the deployment cost.

The useful metric is incremental resident mapping/RSS/PSS after the ordinary wrapper closes, compared under the same workload.

Required A/B/C:

```text
ordinary unload
whole-wrapper NODELETE
split resident bridge
```

For Vulkan whole-wrapper NODELETE, the measured retained mapping delta is 311,296 bytes / 304 KiB.

The bridge prototype should receive the same mapping-level measurement, followed by a minimal generated subset measurement once thunkgen owns the split directly.

## Runtime API impact

A resident bridge implementation can avoid new FEXCore lifetime APIs for the generated helper class because the bridge helper never becomes stale when the ordinary wrapper unloads.

A separate runtime API remains useful for truly reclaimable external targets:

```text
owner/generation registration
retirement state
exact H future-path invalidation
transactional prepare/commit/rollback around destructive VMA replacement
execution quiescence or generation validation
```

This RFC deliberately keeps that heavier mechanism outside the resident helper fast path.

## Proposed implementation sequence

1. Add first-class thunkgen resident-output classification for returned PFN adapters and ordinary callback unpackers.
2. Generate one resident companion per thunk family and bitness.
3. Redirect wrapper lookup/packing to resident helper addresses.
4. Add typed metadata for custom escaping executable helpers.
5. Feed nested callback-member signatures into resident output.
6. Add explicit retained-object metadata for native-retained converted structures.
7. Prove 32-bit behavior.
8. Resolve loader-namespace policy with simultaneous NEWLM tests.
9. Measure incremental residency against selective NODELETE.
10. Consider cross-library deduplication only after semantic identity is explicit.

## Acceptance tests

A first generic bridge implementation should pass all of these classes:

```text
Vulkan dynamic PFN retained across physical wrapper unload
Vulkan X11 callback unpacker retained across wrapper unload
Vulkan forced moved wrapper reload with stable native H
real vulkaninfo compatibility workload
GL dynamic PFN moved-wrapper test
DRM retained callback unpacker moved-wrapper test
DRM generated nested callback-member synchronous test
32-bit dynamic PFN + callback test
multi-namespace independent-state test
```

Every test should retain exact product revision, source delta, wrapper/bridge ELF flags, mapping evidence proving the wrapper actually unloaded when required, and negative controls.

## Open questions for reviewers

1. Should resident companions be per guest loader namespace or private process-global FEX components keyed by family/bitness?
2. Is physical guest wrapper unload/reload a contract worth preserving for these thunk families?
3. Which custom helper interfaces should gain explicit escape metadata first?
4. What ownership syntax best expresses native-retained converted objects?
5. Does the project value bridge-code reclamation during process lifetime enough to justify the heavier owner/quiescence runtime on these generated helpers?

## Evidence boundary

This is a research proposal backed by owned-fork prototypes and hosted CI. It is not an upstream candidate.

The exact historical Apple M5 teardown endpoint remains incompletely captured. The bridge ownership mechanism has independent runtime evidence across Vulkan, GL, and DRM-related callback work.

No third-party/upstream FEX interaction is authorized or performed by this record.
