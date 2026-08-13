# Real FEX LinkAddress lifetime reduction — current source

Date: 2026-08-14

## TL;DR

The guest-thunk lifetime failure now reproduces on **real current FEX** without Vulkan, Mesa, a Vulkan loader, or graphics drivers.

On exact FEX source `71afe476751deac24adabd1adb575fd2337b6e0a`, a retained source-only x86 fixture uses FEX's built-in `fex:link_address_to_function` interface to associate a stable synthetic native identity `H = 0x0000700000010000` with a guest invoker inside an unloadable x86 DSO.

Generation 1 works before unload. `dlclose()` removes the executable mapping containing the guest invoker. The fixture then reserves the old DSO span with `PROT_NONE`, forcing generation 2 to load at a different address. The same synthetic identity `H` still faults with SIGSEGV when executed after reload, while the generation-2 guest invoker works when called directly.

This demonstrates the core stale-generation lifetime defect independently of Vulkan:

```text
stable synthetic identity H
  -> generation-1 guest target T1
  -> T1 executes successfully
  -> guest DSO unloads; T1 becomes unmapped
  -> old span reserved; reload creates T2 at a different address
  -> H still dispatches through generation 1 and faults
  -> direct T2 execution succeeds
```

The result materially promotes Finding B. Vulkan remains the production workload that exposed the problem, but the lifetime mechanism can now be reproduced through FEX's generic LinkAddress/CustomIR path alone.

## Exact identities

- FEX repository: internal owned fork `teamleaderleo/FEX`
- FEX source under test: `71afe476751deac24adabd1adb575fd2337b6e0a`
- disposable hosted carrier branch: `ci/thunk-lifetime-repro-20260814`
- workflow source commit: `a764b38958a40da53100e2728ad7921b725eb799`
- GitHub Actions run: `31732440850`
- artifact: `linkaddress-reload-v2-31732440850`
- artifact id: `9193915118`
- artifact digest: `sha256:b1d3cf6ec4a938f0a0ddf49f8ae025b549b8843a10229e95ad8d842988d4083d`
- Fieldwork fixture source snapshot: `9eca19ac8743567ce2af7b4c82f2483d97c19b09`
- reconstructed fixture archive SHA-256: `0582bf8832699cfb2614c1781473d07054ba01f03e3342735a45ea04735c2a01`
- runner: GitHub hosted `ubuntu-24.04-arm`

## Fixture

The retained fixture lives under [`synthetic-reproducer/`](./synthetic-reproducer/README.md). The hosted run reassembled its source-only archive and built `fex-linkaddress-guest` for x86-64.

The relevant path uses FEX's built-in guest helper:

```text
fex:link_address_to_function
```

The fixture intentionally gives FEX a stable synthetic identity:

```text
H = 0x0000700000010000
```

and links it to a guest invoker exported by `libguest_link_lifetime.so`.

The changed-base case was executed as:

```text
fex_link_lifetime --force-different
```

under the exact built FEX interpreter and amd64 guest rootfs.

## Observed result

The hosted process itself exited `0` because the fixture performs the dangerous stale call in a child and records the child's signal. The distinguishing transcript is:

```text
stable native identity          0x0000700000010000
stable native identity map      0x0000700000010000 -> unmapped

=== generation 1 ===
guest invoker A                 0x00007ffff7da2150 -> ... r-xp .../libguest_link_lifetime.so
guest invoker B                 0x00007ffff7da2170 -> ... r-xp .../libguest_link_lifetime.so
guest DSO span                  00007ffff7da1000-00007ffff7da6000
pre-unload linked call          rv=100071 want=100071
old invoker A after dlclose     0x00007ffff7da2150 -> unmapped
old invoker B after dlclose     0x00007ffff7da2170 -> unmapped
proof: old guest invoker executable mappings disappeared
reserved old DSO span           0x7ffff7da1000 len=0x5000 PROT_NONE
reload invoker A                old=0x00007ffff7da2150 new=0x00007ffff7d9d150 DIFFERENT
old invoker after reload        0x00007ffff7da2150 -> ... ---p
new invoker after reload        0x00007ffff7d9d150 -> ... r-xp .../libguest_link_lifetime.so
child linked entry after reload signal=11 (Segmentation fault)
fresh direct guest invoker      rv=100100071 want=100100071
```

Stderr was empty.

## What this establishes

The result establishes all of these on actual current FEX:

1. The synthetic identity `H` is usable before unload.
2. The generation-1 guest executable target really disappears after `dlclose()`.
3. The old DSO span can be blocked so same-address ABA reuse cannot explain the post-reload behavior.
4. Generation 2 can load at a different address with a working new guest invoker.
5. Calling the old synthetic identity after that changed-base reload still reaches stale generation state strongly enough to produce SIGSEGV.
6. Direct generation-2 guest execution remains healthy.

This is stronger than the earlier native ownership models because it executes FEX's real built-in LinkAddress/CustomIR mechanism.

## Relation to the Vulkan teardown

The Vulkan path reviewed elsewhere is:

```text
native Vulkan PFN H
  -> MakeGuestCallable
  -> LinkAddressToFunction(H, guest CallHostFunction target T)
  -> AddThunkTrampolineIRHandler(H, T)
```

The reduced fixture exercises the same generic LinkAddress lifetime boundary without Vulkan. It therefore removes several competing explanations for the observed production failure:

- Vulkan loader teardown ordering is unnecessary for the core stale-generation behavior;
- Mesa is unnecessary;
- Venus and virtio-gpu are unnecessary;
- Vulkan callbacks are unnecessary;
- a native Vulkan driver is unnecessary.

The production crash still needs its exact immediate predecessor captured if the goal is to prove that Vulkan's terminal transfer is this exact bridge. The generic lifetime defect itself is now runtime-demonstrated independently.

## Design consequences

A repair cannot rely on the target DSO naturally reusing the same address. The forced-different-address control demonstrates the failure across generations.

The evidence supports the owner/generation work already retained in Fieldwork:

- executable guest targets need load-generation identity;
- aliases sharing a synthetic identity need a coherent retirement policy;
- a formerly synthetic identity must remain distinguishable from ordinary guest x86 code after revocation;
- compatible reload/rebind must update or replace the old bridge state;
- stale compiled/cache state must be retired along with registration metadata.

## Next controls

The same real-FEX fixture should now run the wider retained matrix:

1. post-unload stale call before reload;
2. changed-base reload with stale call;
3. alias/same-native-key collision;
4. five forced-different unload/reload cycles;
5. pin/no-unload control;
6. a candidate retirement/rebind mechanism once the exact synthetic-key cache eviction path is verified.

A sibling real-FEX host-to-guest callback unload reduction remains valuable because that bridge family stores raw guest unpacker/target PCs independently of the LinkAddress path.

## Evidence limits

- This fixture deliberately uses a synthetic stable address instead of a real native Vulkan PFN.
- The child SIGSEGV proves stale linked execution after changed-base reload; this run did not yet instrument the exact internal cache object selected immediately before the fault.
- The fixture covers one thread and one LinkAddress identity in this run.
- Multi-owner callback dependencies, concurrent execution drain, repeated-cycle behavior, and pinning are follow-up gates.

## External-contact state

None. No FEX upstream interaction was made.
