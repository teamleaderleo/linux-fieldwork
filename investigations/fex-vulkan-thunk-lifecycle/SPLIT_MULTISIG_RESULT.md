# Multi-signature resident Vulkan bridge result

## Result

**The lifetime experiment passed.** A hosted ARM64 run on pristine FEX main `71afe476751deac24adabd1adb575fd2337b6e0a` successfully kept three different real Vulkan dynamic PFNs callable across physical unload of the ordinary guest Vulkan wrapper and across a forced different-base wrapper reload.

GitHub Actions run: `teamleaderleo/FEX` run `31778261393`, attempt 3 job `94700002123`.

FEX experiment branch: `ci/split-vulkan-bridge-multisig-20260814`.

The job's final GitHub conclusion is red only because a stale grep assertion expected `vulkan-maps=0 bridge-maps=...`; the corrected probe now inserts `all-vulkan-maps=4` between those fields. Both actual probe modes exited 0 and all substantive lifetime assertions before that stale grep succeeded.

## Three distinct resident signature adapters

The resident `DF_1_NODELETE` bridge initialized three distinct guest executable adapters:

```text
SPLIT_BRIDGE_READY version=0x7ffff7e43260 layers=0x7ffff7e432b0 extensions=0x7ffff7e43310
```

They were linked to three real native Vulkan PFNs:

```text
vkEnumerateInstanceVersion:
    H=0x7ffff76c80f4
    T=0x7ffff7e43260

vkEnumerateInstanceLayerProperties:
    H=0x7ffff76c8704
    T=0x7ffff7e432b0

vkEnumerateInstanceExtensionProperties:
    H=0x7ffff76c8424
    T=0x7ffff7e43310
```

The guest Vulkan wrapper itself was verified not to contain `DF_1_NODELETE`.

## Physical-close result

Generation 1 had five exact guest-wrapper mappings. Before close all three calls succeeded:

```text
PROBE return where=before-close
    version-result=0 version=0x403113
    layers-result=0 layers=3
    extensions-result=0 extensions=24
    vulkan-maps=5
    all-vulkan-maps=9
    bridge-maps=5
```

After real `dlclose()` the exact guest Vulkan wrapper mapping count became zero. Four host-side Vulkan mappings remained in FEX's process, which is why the probe now reports both exact guest-wrapper and broad `libvulkan.so.1` counts:

```text
PROBE after-close vulkan-maps=0 all-vulkan-maps=4 bridge-maps=5
```

With the guest wrapper absent, all three retained PFNs still succeeded:

```text
PROBE call where=after-real-close-old-pfns ... vulkan-maps=0 all-vulkan-maps=4 bridge-maps=5
PROBE return where=after-real-close-old-pfns
    version-result=0 version=0x403113
    layers-result=0 layers=3
    extensions-result=0 extensions=24
    vulkan-maps=0
    all-vulkan-maps=4
    bridge-maps=5
PROBE close-mode-pass
```

The close-mode guest process exited 0.

## Forced changed-base reload result

The probe reserved all five old wrapper ranges with `PROT_NONE` before reopening Vulkan:

```text
PROBE reserved-old-generation-ranges=5
```

Generation 2 therefore loaded at a substantially different address:

```text
old-gipa=0x7ffff7ea25b0
new-gipa=0x7fffe5e715b0
```

Despite the wrapper moving, all three native PFNs remained exactly the same:

```text
old-version=0x7ffff76c80f4 new-version=0x7ffff76c80f4 same-version=1
old-layers=0x7ffff76c8704 new-layers=0x7ffff76c8704 same-layers=1
old-extensions=0x7ffff76c8424 new-extensions=0x7ffff76c8424 same-extensions=1
```

The bridge reinitialized to the exact same three resident T addresses:

```text
version=0x7ffff7e43260
layers=0x7ffff7e432b0
extensions=0x7ffff7e43310
```

Both the freshly acquired generation-2 PFNs and the retained generation-1 PFNs succeeded:

```text
PROBE return where=after-reload-new-pfns
    version-result=0
    layers-result=0
    extensions-result=0

PROBE return where=after-reload-old-pfns
    version-result=0
    layers-result=0
    extensions-result=0
```

After the second real close:

```text
PROBE after-second-close vulkan-maps=0 all-vulkan-maps=4 bridge-maps=5
PROBE reload-mode-pass
```

The reload-mode guest process also exited 0.

## What this proves

The earlier one-function result was not a special property of `vkEnumerateInstanceVersion`.

At least three materially different generated `CallHostFunction<signature>` adapters can be process-resident while the ordinary Vulkan wrapper is physically unloadable. The adapter addresses stay stable across a forced wrapper-generation move, and the corresponding native PFNs remain callable both while the wrapper is absent and after a new wrapper generation appears elsewhere.

This strengthens the ownership rule:

> Immutable generated signature adapters have a useful lifetime broader than the guest wrapper DSO that requested them.

It also shows that a resident bridge runtime can hold multiple distinct ABI adapters simultaneously, rather than relying on one lucky universal trampoline.

## CI bookkeeping note

The Actions job's final failure is not an experimental failure. It happened after both `close` and `reload` probes exited 0. The stale assertion was:

```text
grep -q 'PROBE after-close vulkan-maps=0 bridge-maps='
```

The corrected probe output is:

```text
PROBE after-close vulkan-maps=0 all-vulkan-maps=4 bridge-maps=5
```

The extra field was intentionally added to distinguish exact guest-wrapper mappings from native host Vulkan-loader mappings visible in FEX's process.
