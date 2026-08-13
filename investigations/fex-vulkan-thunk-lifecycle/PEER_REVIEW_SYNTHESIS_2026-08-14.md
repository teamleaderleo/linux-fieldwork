# Peer review synthesis — FEX Vulkan callback routing and guest-thunk lifetime

Date: 2026-08-14

## TL;DR

The independent lanes converge on two defects with different evidence strength.

**Finding A: dynamic Vulkan callback routing.** The retained FEX-2608/M5 A/B already demonstrates that dynamic lookup of `vkCreateDebugReportCallbackEXT` can bypass FEX's existing callback-aware custom implementation. Routing that lookup to the existing custom implementation removes the earlier SIGILL and allows enumeration. Current reviewed FEX source `71afe476751deac24adabd1adb575fd2337b6e0a` still contains the metadata/handwritten-lookup mismatch. Agent A and Agent B independently widen the review to `vkDestroyDebugReportCallbackEXT` and `vkCreateDebugUtilsMessengerEXT`.

**Finding B: guest-thunk lifetime.** The retained teardown controls strongly localize the exit-139 failure to an unloadable FEX guest Vulkan thunk while FEX-owned execution state survives. Dynamic-PFN CustomIR remains the leading immediate mechanism. A second source-confirmed stale-address reservoir exists in host-to-guest callback trampoline metadata. The real Vulkan crash still needs the immediate post-unload transfer captured.

The strongest lifetime invariant after peer review is:

> Every FEX-owned executable bridge that depends on guest code must carry enough owner/load-generation information to revoke every executable dependency before the corresponding guest executable mapping disappears. A revoked synthetic identity must remain distinguishable from ordinary guest code until safely rebound or permanently retired.

## Review set

This pass reviewed:

- [`ARCHITECTURE_RATIONALE.md`](./ARCHITECTURE_RATIONALE.md)
- [`ADVERSARIAL_REVIEW.md`](./ADVERSARIAL_REVIEW.md)
- [`CUSTOM_IR_FINDINGS.md`](./CUSTOM_IR_FINDINGS.md)
- [`HISTORY_COMPATIBILITY.md`](./HISTORY_COMPATIBILITY.md)
- [`DYNAMIC_CUSTOM_ROUTING_AUDIT.md`](./DYNAMIC_CUSTOM_ROUTING_AUDIT.md)
- [`agent-b/README.md`](./agent-b/README.md) and [`agent-b/SOURCE_REVIEW_RECEIPT.md`](./agent-b/SOURCE_REVIEW_RECEIPT.md)
- [`HOSTED_ARM64_FINDING_A.md`](./HOSTED_ARM64_FINDING_A.md) and [`HOSTED_ARM64_FINDING_A_RUNS.md`](./HOSTED_ARM64_FINDING_A_RUNS.md)
- [`lifetime-designs/DESIGN_COMPARISON.md`](./lifetime-designs/DESIGN_COMPARISON.md)
- [`lifetime-designs/FEX_INTEGRATION_NOTES.md`](./lifetime-designs/FEX_INTEGRATION_NOTES.md)
- the owner-generation registry probe
- the multi-owner bridge dependency model
- [`synthetic-reproducer/README.md`](./synthetic-reproducer/README.md)
- [`../../notes/processes/fex-thunk-bridges-must-retire-before-guest-dso-unmap.md`](../../notes/processes/fex-thunk-bridges-must-retire-before-guest-dso-unmap.md)

## Finding A review

The original callback-routing claim survives challenge. The runtime A/B is causal, and the source mismatch remains on the reviewed current source snapshot.

Agent A adds a required semantic boundary: native GIPA/GDPA availability should remain authoritative. A complete repair should substitute FEX's custom implementation only when the native loader reports that command as available.

Two sibling mismatches deserve separate runtime checks:

- `vkDestroyDebugReportCallbackEXT`, especially with non-null allocation callbacks;
- `vkCreateDebugUtilsMessengerEXT`, another callback-bearing create path.

Agent B's reduced callback probes are especially useful because they finish before normal Vulkan teardown, separating Finding A from Finding B.

### Hosted ARM64 correction

The first hosted current-main run looked green at the workflow level but every x86/FEX discriminator returned 255. Its stderr reported that `FEXServer` could not be executed. No guest probe body ran.

The hosted repair now explicitly builds and asserts `FEXServer`. That change succeeded through FEX, FEXServer, host Vulkan thunk, and guest Vulkan thunk builds. The next first owner was a fixture warning promoted to an error: the inline phase probe ignored `write()` under `-Werror`. The v2 workflow now verifies the byte count and leaves every downstream Finding A discriminator unchanged.

Current hosted lane at this record's creation:

- owned repo: `teamleaderleo/FEX`
- branch: `ci/agent-c-finding-a-arm64-20260814`
- workflow source commit: `870ebd7bc261c5e23f124e865a25cce03c01a72a`
- exact FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`
- v2 run: `31731042229`
- state: running

Interpret the artifact's phase classification rather than the overall workflow conclusion.

## Finding B review

Dynamic-PFN CustomIR remains the leading mechanism. The reviewed source path is:

`native PFN -> MakeGuestCallable -> LinkAddressToFunction -> AddThunkTrampolineIRHandler -> guest CallHostFunction target in the unloadable guest DSO`.

The retained target controls remain strong: no-op guest `dlclose` and pinning only `libvulkan-guest.so` each change exit 139 to exit 0; a bogus preload preserves exit 139; llvmpipe preserves the teardown failure.

The seventh-pass review also shows that simple registration erasure is too weak. CustomIR blocks can remain compiled under a synthetic native-PFN key without an ordinary guest-code-page dependency, so retirement must also handle exact shared and per-thread cache state.

### New source finding: host-callback cache has the same lifetime family

Current reviewed `Thunks.cpp` keeps `GuestcallToHostTrampoline` entries keyed by guest unpacker/target addresses. Each trampoline instance copies raw `GuestUnpacker` and `GuestTarget` values. No matching retirement path was found in the reviewed thunk handler.

A host callback can therefore depend on more than one guest load generation. For example, a Vulkan-owned unpacker may route to an X11-owned guest target. Revoking either dependency must make that bridge unusable. This supports the newer multi-owner dependency model over a single “creator DSO” field.

### New source finding: GuestMunmap invalidation is post-unmap

At reviewed current source, the 64-bit `GuestMunmap()` path performs the real `munmap`, updates VMA tracking, and then invokes ordinary code invalidation.

That order fits ordinary guest translation state tied directly to the removed guest range. Hidden bridge metadata needs an earlier retirement/revocation phase if it contains executable guest dependencies.

### New source finding: code invalidation is not an execution lease

Lookup/compilation holds `CodeInvalidationMutex` shared; invalidation takes it uniquely. Actual translated execution happens after the lookup/compile scope returns.

The 15/15 stable-slot + generation + execution-lease model therefore remains an upper-bound concurrent design. Production FEX needs the drain component where a legally in-flight FEX-owned bridge can overlap retirement and existing synchronization supplies no equivalent guarantee. The retained single-thread Vulkan crash does not require that stronger race to explain it.

## Lifetime design review

The 22/22 owner-generation model is the strongest compact identity model so far. It preserves formerly synthetic PFNs as synthetic after unload, supports compatible reload, rejects incompatible signature reuse, revokes aliases together, and leaves unrelated owners active.

The multi-owner bridge model extends that requirement to callback trampolines whose executable dependencies span multiple guest generations.

NODELETE/residency remains a plausible containment policy. The existing target pin control already proves that guest-thunk residency prevents the observed teardown crash. Local glibc probes also show that a guest DSO can promote itself by SONAME to `RTLD_NODELETE`, including from its constructor. A real FEX target run of the owned self-promotion candidate is still required.

## Next experiment ladder

1. Finish the hosted current-main Finding A discriminator: static x86 smoke, dynamic plain, guest Vulkan load, direct callback control, GIPA baseline, then the same GIPA probe with only diagnostic custom routing changed.
2. Run the real FEX `fex:link_address_to_function` lifetime reduction from [`synthetic-reproducer`](./synthetic-reproducer/README.md), including stale call, changed-base reload, stable native identity reuse, alias case, repeated cycles, and pin control.
3. Build a sibling reduced host-to-guest callback unload case to determine whether the callback cache is executable evidence or only a latent source-level class.
4. Run the owned NODELETE guest-wrapper candidate against the real FEX Vulkan target and compare it with the known external pin control.
5. On the retained M5/FEX-2608 fault, inspect guest R11. The dynamic-PFN CustomIR path writes the native PFN to guest R11 immediately before exiting to the guest `CallHostFunction` target. A match to a previously registered Vulkan PFN would close the immediate-predecessor gap cheaply.

## Evidence limits

- retained M5 runtime evidence executes FEX-2608; current main is source-reviewed and is being tested separately on hosted ARM64;
- owner/generation and multi-owner graph work are semantic models rather than integrated FEX changes;
- callback-trampoline stale guest PCs are source-confirmed and still need a reduced runtime unload result;
- NODELETE has local glibc loader evidence plus the existing target pin control; the owned FEX self-promotion candidate still needs target execution;
- current hosted Finding A results remain harness evidence until the artifact proves guest probe bodies ran.

## External-contact state

None. No FEX upstream issue, pull request, comment, review, or other interaction was created by this review.
