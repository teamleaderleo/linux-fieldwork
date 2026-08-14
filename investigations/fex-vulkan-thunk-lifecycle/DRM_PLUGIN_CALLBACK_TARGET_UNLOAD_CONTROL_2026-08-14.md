# DRM resident unpacker with unloadable callback-target plugin: control

Date: 2026-08-14
Status: deterministic real-API failure control
Scope: owned FEX/fieldwork surfaces only

## Result

A process-resident generated DRM callback unpacker does not extend the lifetime of the application callback target that native libdrm retains.

Exact hosted ARM64 receipt:

```text
branch:   ci/drm-loadmodule-plugin-unload-control-20260814
head:     459237cf21d0afc6494aff8e0a72f97c108f50e9
run:      31794597897
job:      94748801297
artifact: drm-plugin-target-control-31794597897
id:       9216959036
sha256:   e83e076651adda8d50b1cf079f5eab8b031f2038528ec009410ea147b3ca8468
observed runtime exit: 139
```

The workflow is green as an observational control. It requires the callback to enter and the plugin close operation to return; the recorded application exit is the discriminator result.

## Setup

This control starts from the already-proven generated resident bridge for `drmServerInfo::load_module`:

```text
libfex-drm-bridge.so -> NODELETE
ordinary libdrm guest wrapper -> unloadable, NEEDED bridge
callback-member conversion -> generated
```

The application callback target is moved into a separate guest plugin DSO:

```text
libdrm-callback-plugin.so
  drm_plugin_load_module
```

The main guest registers that plugin function through `drmSetServerInfo`, starts `drmOpen` on another guest thread, and waits until native libdrm has invoked the callback and the plugin callback is blocked.

Only then does the main thread `dlclose` the plugin.

## Exact runtime boundary

The callback target begins mapped:

```text
DRM_PLUGIN_PROBE set-info callback=0x7ffff7ead1e0 mapped=1
DRM_PLUGIN_PROBE open-enter
DRM_PLUGIN callback-enter name=fex-intentionally-missing-drm-driver self=0x7ffff7ead1e0
DRM_PLUGIN_PROBE callback-blocked mapped-before-close=1
```

The plugin then physically unloads while the callback is already active:

```text
DRM_PLUGIN_PROBE plugin-close rc=0 mapped-after-close=0 worker-returned=0
```

The controller releases the blocked callback:

```text
DRM_PLUGIN_PROBE released
timeout: the monitored command dumped core
exit=139
```

The callback never reaches its post-release return marker.

## Interpretation

This is a real libdrm counterpart to the synthetic callback in-flight race.

The generated resident bridge correctly keeps the **generated callback unpacker** alive. The crash occurs because the actual application callback target belongs to an independently unloadable guest DSO and is physically removed while execution is in flight.

That establishes the ownership split on a real retained-callback API:

```text
generated GuestUnpacker
  -> resident companion lifetime works

application GuestTarget
  -> still requires application/load-generation retirement + execution lease
```

The resident bridge is therefore complementary to owner-generation callback leases rather than a substitute for them.

## Next integration

Compose the OwnerID execution-lease mechanism with this DRM carrier, but key the lease on the callback **target** generation while accepting a separate resident unpacker generation.

The current synthetic OwnerID prototype deliberately requires:

```text
UnpackerOwnerID == TargetOwnerID
```

That requirement must be relaxed for the resident-companion architecture because the whole point of the split is that unpacker and target have distinct owners.

For the first real integration:

```text
GuestUnpacker -> libfex-drm-bridge.so, process resident
GuestTarget   -> libdrm-callback-plugin.so, unloadable
```

The lease can therefore attach to `TargetOwnerID` while treating the bridge owner as process-resident.

A likely further boundary is that VMA OwnerID covers one mapping rather than the whole plugin load. If the callback returns through text while also requiring GOT/rodata/data mappings that `dlclose` has already removed, pinning only the target text VMA may still fail. That result would directly motivate `LoadGenerationID` or an owner-dependency set grouping all mappings required by the plugin generation.
