# Review of the first CustomIR unload-cleanup candidate

This note records why the original `candidate-range-cleanup.patch` remains useful evidence but is no longer the preferred production design.

Related:

- [CUSTOM_IR_FINDINGS.md](./CUSTOM_IR_FINDINGS.md)
- [HISTORY_COMPATIBILITY.md](./HISTORY_COMPATIBILITY.md)
- [candidate-range-cleanup.patch](./candidate-range-cleanup.patch)
- [probe-results.txt](./probe-results.txt)
- [retirement-probe-results.txt](./retirement-probe-results.txt)
- [owner-registry-probe-results.txt](./owner-registry-probe-results.txt)

## What the first candidate established

The first candidate did two things when a guest target range disappeared:

1. erased thunk-owned `CustomIRHandlers` entries whose `Data` pointed into the range;
2. invalidated translated code at the corresponding synthetic/native host-PFN keys.

That split remains important. Current source confirms that a compiled CustomIR entry **does enter the runtime `LookupCache`**:

```text
CompileBlock
  -> CompileCode / GenerateIR
  -> CompiledCode.EntryPoints
  -> LookupCache->AddBlockMapping(Thread, GuestAddr, CodePages, HostAddr)
```

For CustomIR, `NeedsAddGuestCodeRanges` is false, so ordinary guest executable-page tracking is skipped. `CodePages` can consequently be empty, but `AddBlockMapping` still installs the synthetic key.

Therefore the source comment in `AddThunkTrampolineIRHandler` that thunk entrypoints “don't get cached” cannot mean “they are absent from the runtime lookup cache.” It is consistent with them being excluded from ordinary guest-page/persistent code-cache tracking while still having a runtime dispatch mapping.

This supports the original two-layer result:

```text
registry-only retirement can leave a compiled synthetic-key mapping
cache-only retirement can allow the surviving handler to regenerate the mapping
```

## Why raw erase is now demoted

### Synthetic addresses need a post-retirement meaning

A native host PFN is intentionally exposed as the guest-visible function pointer.

While a matching CustomIR entry exists, FEX recognizes that host-native numeric address as a synthetic guest entrypoint. If the CustomIR entry is erased and its runtime mapping is invalidated, the next lookup can fall through to normal x86 decoding at that numeric address.

That means an expired pointer may transition from:

```text
synthetic host PFN -> guest wrapper
```

to:

```text
ordinary guest RIP -> decode bytes at host PFN
```

On an ARM host, the latter can mean attempting to decode native ARM instructions as x86. Native `dlclose` semantics make use of an expired function pointer invalid, but FEX should still preserve the distinction between an ordinary guest address and a value it previously advertised as a synthetic callable host address.

The revised semantic model therefore keeps a tombstone/revoked entry for previously synthetic keys.

## Revised minimum state machine

```text
unknown
  | registration
  v
active(host key H, guest target T, owner generation G, signature S)
  | owner G retires
  v
revoked/tombstone(H, S)
  | compatible reload/rebind
  v
active(H, T2, G2, S)
```

Dispatch behavior:

```text
unknown key       -> ordinary frontend decode
active key        -> guest target
revoked key       -> deterministic rejection/guest fault
```

A revoked key must also invalidate any previously compiled runtime `LookupCache` mapping so dispatch reaches the new revoked handler/state.

## Why an owner generation is preferable to a raw target range

Current Linux VMA tracking already has a close approximation of an ELF load-instance object: `VMATracking::MappedResource`.

Important current behavior:

- mappings of the same file share an `MRID` where appropriate;
- if an ELF header is mapped again, FEX creates another `MappedResource` for the new base/load;
- each `MappedResource` owns the linked set of VMA entries for that mapping instance;
- `DeleteVMARange` removes the resource once its final mapping is gone.

This is stronger than identifying an owner only by target address range because:

- one ELF load has multiple VMAs;
- partial unmaps should not necessarily retire the whole DSO if executable target mappings remain;
- a later load can reuse the same virtual addresses;
- the same backing file can be mapped into multiple independent bases.

A production implementation could give each `MappedResource` a monotonic thunk/load generation ID, or derive an equivalent stable owner token while the resource exists.

At `LinkAddressToGuestFunction`, FEX can query the VMA containing `target_addr` and associate the synthetic host-PFN claim with that load generation.

## Registration compatibility requires more metadata

Current `AddCustomIREntrypoint` is first-insertion-wins. `AddThunkTrampolineIRHandler` tolerates a same-creator collision and logs when the same host PFN is already linked to another guest target. Its source comment explicitly names Vulkan aliases such as:

```text
vkGetPhysicalDeviceFeatures2
vkGetPhysicalDeviceFeatures2KHR
```

The original 2022 review also considered collisions across libraries.

A robust unload owner therefore cannot discard every non-winning registration. Consider:

```text
load A: H -> T1
load B: H -> T2
```

If B's claim is thrown away while A is active, unloading A leaves no information that B may still need `H`.

The new owner-registry model retains all claims and promotes a surviving claim only when its signature identity is compatible with the established entry.

## Signature identity is available conceptually, but not in the current Link API

FEX's function-pointer machinery evolved toward signature-based adapters. Current generator code computes callback thunk hashes from:

```text
"fexcallback_" + function_pointer_signature
```

That gives the design a natural ABI identity for deciding whether two guest wrapper claims are interchangeable.

Current `LinkAddressToFunction(addr, target)` sends only:

```text
original_callee
target_addr
```

so Core cannot distinguish:

- two equivalent wrappers for the same signature in different DSOs;
- two genuinely incompatible wrappers that happen to share a native host address.

A generic multi-owner implementation likely needs to extend registration metadata with a signature ID or equivalent generated identity.

A smaller implementation could retain multiple targets without auto-promotion and require a fresh proc-address lookup to rebind after the active owner unloads. That is safer than guessing, but it can break a still-live second DSO that already holds the same native PFN.

## `SMCCHECKS=none` remains a correctness trap for the existing remove API

Current `ContextImpl::RemoveCustomIREntrypoint` erases the handler and calls:

```text
SyscallHandler->InvalidateGuestCodeRange(Thread, Entrypoint, 1)
```

On Linux this routes through `InvalidateCodeRangeIfNecessary`, which suppresses the actual `ThreadManager::InvalidateGuestCodeRange` operation when SMC checking is disabled.

That policy is unsuitable for a synthetic key whose compiled code contains a hidden guest-DSO dependency. Retirement of a synthetic bridge must invalidate the runtime key regardless of the guest SMC mode.

The direct `ThreadManager` implementation already supplies a suitable synchronization pattern: acquire thread-creation and code-invalidation synchronization, invalidate code buffers, then invalidate each thread's lookup-cache range.

## `munmap` ordering and resource identity

Current `GuestMunmap` performs the real host `munmap` before `TrackMunmap` removes VMA metadata, and then performs ordinary code-range invalidation after VMA tracking has been updated.

For owner-aware thunk retirement, this ordering creates two implementation choices.

### Post-unmap retirement

Advantages:

- only retire when `munmap` actually succeeds;
- simple failure behavior.

Cost:

- a short window exists where a synthetic bridge still names code that has already disappeared.

This may be acceptable under native `dlclose` synchronization assumptions, but should be tested with a concurrent caller rather than assumed.

### Staged pre-unmap revocation

Possible order:

```text
collect affected load-generation owners under VMA lock
mark their synthetic bridges draining/revoked
invalidate compiled synthetic keys
perform munmap
commit VMA/resource retirement
```

A failed `munmap` then needs either rollback to active state or a two-phase state whose target remains recoverable until commit.

This is stronger under concurrency and closer to the existing `lease_slot` experiment, with more bookkeeping.

## mprotect and mremap broaden the generic lifetime question

A bridge is unsafe whenever its guest executable target ceases to be a valid executable destination, regardless of whether that happens through `dlclose`.

Current FEX also tracks:

- `mprotect` and code-range invalidation;
- `mremap`, including moved/shrunk ranges;
- mapping replacement through the VMA tracker.

A load-generation owner can centralize these cases more cleanly than a Vulkan-specific `dlclose` callback. The immediate Vulkan reproducer uses ordinary unload/`munmap`, so implementation should start there and add explicit controls for `mremap`/execute-permission removal before claiming a complete generic invariant.

## Adjacent host-to-guest trampoline owner

`GuestcallToHostTrampoline` remains a second bridge family. Each trampoline embeds:

```text
GuestUnpacker
GuestTarget
```

A VMA/load-generation retirement callback could revoke or retire those entries using the same owner identity as CustomIR. This is attractive because it addresses both known guest-address-retention mechanisms with one lifecycle owner.

The exact Vulkan crash still fits the dynamic-PFN/`CallHostFunction` path better, so this adjacent cache should be instrumented rather than folded into the causal claim prematurely.

## Probe status

Three retained synthetic/model layers now exist:

1. [`probe-results.txt`](./probe-results.txt): **34/34** — executable mmap/munmap mechanism test proving handler+compiled-state dual retirement.
2. [`retirement-probe-results.txt`](./retirement-probe-results.txt): **13/13** — erase versus tombstone/rebind semantics and first-wins cross-owner limitation.
3. [`owner-registry-probe-results.txt`](./owner-registry-probe-results.txt): **22/22** — load-generation owner, compatible-claim promotion, incompatible-signature rejection, aliases, reload, unrelated owner preservation.

These are engineering models. They do not replace the missing real FEX causal trace.

## Current preferred direction

The smallest design that currently respects the historical compatibility constraints is:

```text
synthetic native PFN key H
  -> persistent entry identity
  -> one or more owner-generation claims
       guest target
       generated signature/ABI identity
       load generation
  -> active / revoked state
```

On guest load retirement:

1. identify the retiring load generation from VMA/resource state;
2. remove its claims;
3. if a compatible live claim remains, promote it;
4. otherwise leave a revoked/tombstoned synthetic key;
5. invalidate the runtime synthetic key independently of SMC configuration;
6. let compatible later registrations rebind the key.

This preserves the feature's original native-pointer identity goal, handles reload, avoids host-byte frontend decode, and creates a path toward cross-library ownership.

Before implementation is treated as a real fix, capture the actual Vulkan `REGISTER -> UNMAP -> CUSTOMIR HIT -> FAULT` trace. If the post-unload CustomIR hit is absent, this design still repairs a real lifetime hazard, but another bridge owns the observed teardown crash.
