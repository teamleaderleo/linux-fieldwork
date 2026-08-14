# DRM retained callback: resident unpacker + unloadable target-owner lease

Date: 2026-08-14
Status: successful real-API hosted ARM64 proof
Scope: owned FEX/fieldwork surfaces only

## Result

The two independently proven halves of the callback lifetime design now work together on a real retained libdrm callback:

```text
GuestUnpacker -> generated NODELETE DRM resident bridge
GuestTarget   -> separately unloadable guest plugin DSO
```

The callback execution lease is keyed only to the unloadable target owner while the resident unpacker is allowed to have a different owner generation.

Exact receipt:

```text
branch:   ci/drm-loadmodule-plugin-target-owner-lease-20260814
head:     ad4064459743e625c6d24c189f586f76a45638db
run:      31795226518
job:      94750741774
result:   success
artifact: drm-plugin-target-owner-lease-31795226518
id:       9217186410
sha256:   0d895dd7470bfc4b3cdc9977974b8d52d5e3b5c949a7e3634bf3eb154589d45e
runtime:  0
```

The combined candidate builds on current upstream FEX head:

```text
f3ab82a73fb48271ee12a882c98bc5d823a2b4d1
```

and composes the generated DRM resident-bridge patch with the OwnerID callback lease stack.

## Split executable ownership is observed directly

At `drmSetServerInfo` callback registration:

```text
GuestUnpacker = 0x7ffff7eb22e0
GuestTarget   = 0x7ffff7ead1e0
```

FEX resolves different owner identities:

```text
DIAG_CALLBACK_OWNER_SPLIT
  unpacker_owner=0x11
  target_owner=0x12
```

The resident bridge owner is therefore distinct from the application callback plugin owner, exactly as intended by the architecture.

The callback descriptor is attached to target owner `0x12`:

```text
DIAG_CALLBACK_OWNER_CREATE owner=0x12
DIAG_CALLBACK_DESCRIPTOR_CREATE ... owner=0x12
```

## Real retained callback enters through native libdrm

The application registers `drm_plugin_load_module` in `drmServerInfo`, then a guest pthread calls `drmOpen` and native libdrm invokes the retained callback:

```text
DRM_PLUGIN_PROBE open-enter
DIAG_CALLBACK_OWNER_ACQUIRE owner=0x12 active=1
DRM_PLUGIN callback-enter name=fex-intentionally-missing-drm-driver self=0x7ffff7ead1e0
DRM_PLUGIN_PROBE callback-blocked mapped-before-close=1
```

This is a native-libdrm-retained callback, not a synthetic host helper.

## Plugin dlclose retires the target owner without removing it underneath execution

While the callback remains blocked, the main guest thread closes the plugin DSO.

FEX retires owner `0x12` across the plugin range:

```text
DIAG_CALLBACK_OWNER_RETIRE owner=0x12 active=1 defer=1 range=0x7ffff7eac000+0x5000
DIAG_CALLBACK_DESCRIPTOR_RETIRE ... owner=0x12
DIAG_CALLBACK_OWNER_DEFER_HOST_UNMAP range=0x7ffff7eac000+0x5000
```

Guest `dlclose` returns, but the callback target is still physically mapped because its owner lease is active:

```text
DRM_PLUGIN_PROBE plugin-close rc=0 mapped-after-close=1 worker-returned=0
```

This is the direct positive counterpart to the previous real-API control:

```text
resident unpacker only:
  plugin-close rc=0 mapped-after-close=0
  release -> 139
```

## Active callback resumes and returns normally

After the controller releases the callback:

```text
DRM_PLUGIN_PROBE released
DRM_PLUGIN callback-resume byte=82
DRM_PLUGIN callback-return
```

The target owner lease then drops to zero:

```text
DIAG_CALLBACK_OWNER_RELEASE owner=0x12 active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_BEGIN owner=0x12 range=0x7ffff7eac000+0x5000
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0x12 range=0x7ffff7eac000+0x5000 result=0
```

Native libdrm returns from the triggering operation and the plugin callback mapping is finally gone:

```text
DRM_PLUGIN_PROBE open-return fd=-1
DRM_PLUGIN_PROBE joined fd=-1 mapped-after-join=0
```

Process exit is `0`.

## What this proves

For this real libdrm retained-callback path, the proposed ownership split is viable:

```text
resident generated companion
  owns the generated native->guest callback unpacker for process lifetime

application plugin owner generation
  owns the actual guest callback target

callback execution lease
  pins only the unloadable target generation while it is already executing

generation retirement
  lets guest dlclose return, blocks future use of the retired descriptor, and defers physical target-owner reclaim
```

The resident generated bridge does not need to participate in reclaimable execution leasing because its generated unpacker is intentionally process-resident.

## Important OwnerID observation

The plugin's callback target resolves to owner `0x12`, and plugin unload retires a contiguous `0x5000` range under the same owner identity in this fixture.

The earlier concern that one callback-text VMA might be pinned while sibling plugin mappings disappeared does not reproduce here: the callback resumes through its `fprintf`, string/GOT/data dependencies and returns successfully before the `0x5000` owner range is reclaimed.

That is encouraging evidence that the experimental ownership stack can represent this normal small ELF plugin generation coherently.

It is not yet a proof that every ELF/load topology maps one-to-one to a single OwnerID. Multi-segment/multi-resource DSOs, split mappings, remap/protection transformations, namespaces, and JIT/application-generated code still need explicit ownership tests before calling VMA OwnerID a complete `LoadGenerationID`.

## Current architecture after this result

The strongest demonstrated callback design is now:

```text
1. thunkgen marks callback semantics explicitly (`callback_member` / typed callback metadata)
2. generated callback unpacker lives in a resident per-library guest companion
3. ordinary guest thunk wrapper may physically unload/reload
4. retained application callback descriptor points at the callback target's owner generation
5. callback entry acquires target-generation execution lease
6. retirement immediately removes future registration/entry and returns without synchronous drain
7. physical target-generation reclaim waits for the last execution lease
8. memory replacement paths must respect active owner leases
```

The synthetic MAP_FIXED reject/retry proof now supplies step 8 for one destructive mapping path.

## Next real-API gates

### A. Future stale retained callback after plugin unload

After the first callback returns and the plugin generation is reclaimed, trigger libdrm again without re-registering `drmServerInfo`.

Expected result:

```text
old retained native callback -> stable FEX-owned descriptor -> controlled revoke 113
```

Run this in a child process so the expected revoke does not destroy the controller.

### B. Reload plugin and register generation 2

Reload the plugin, preferably forcing moved address first, and register a fresh `drmServerInfo` callback.

Require:

```text
old generation callback -> revoked
new generation callback -> works
new target owner identity -> fresh/non-reused
```

Then add a same-address ABA variant if the loader can be forced to reuse the old guest callback address.

### C. Multi-callback same-owner aggregation

Register two callback descriptors whose targets belong to the same plugin generation and hold both active while unloading.

Physical reclaim must wait for the **aggregate owner active count** to reach zero, proving that the owner-level counter solves the per-descriptor reclamation bug the earlier prototype could have had.

### D. Memory-operation audit

Extend active-owner arbitration beyond explicit `munmap` and MAP_FIXED. `mremap` is the highest-priority uncovered physical mapping transition on current FEX main.
