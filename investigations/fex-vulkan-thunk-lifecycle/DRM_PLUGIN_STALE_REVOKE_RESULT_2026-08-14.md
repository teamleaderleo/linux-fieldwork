# Real DRM retained callback stale-revoke result

Date: 2026-08-14
Status: green runtime proof
Scope: owned FEX/fieldwork surfaces only

## Result

A real `drmServerInfo::load_module` callback now demonstrates the complete future-entry contract after physical callback-target reclamation.

The generated DRM callback unpacker is process-resident in the generated DRM bridge. The actual guest callback target lives in a separately unloadable guest plugin and carries its own VMA OwnerID.

The target-owner lease allows an already-entered callback to finish after guest `dlclose(plugin)` returns. Once the last lease releases, the plugin generation is physically reclaimed. Native libdrm still retains the old callback registration, so a second libdrm-triggered callback is a real stale-entry test rather than a synthetic direct trampoline call.

Observed sequence:

```text
unpacker owner = 0x11
target owner   = 0x12

DIAG_CALLBACK_OWNER_ACQUIRE owner=0x12 active=1
DRM_PLUGIN callback-enter
DIAG_CALLBACK_OWNER_RETIRE owner=0x12 active=1 defer=1
DRM_PLUGIN_PROBE plugin-close rc=0 mapped-after-close=1
DRM_PLUGIN callback-resume
DRM_PLUGIN callback-return
DIAG_CALLBACK_OWNER_RELEASE owner=0x12 active=0 deferred=1
DIAG_CALLBACK_OWNER_RECLAIM_DONE owner=0x12 ... result=0
DRM_PLUGIN_PROBE joined fd=-1 mapped-after-join=0

DRM_PLUGIN_PROBE stale-child-enter
DIAG_CALLBACK_OWNER_REVOKED owner=0x12 ... state=1 active=0
DRM_PLUGIN_PROBE stale-child exit=113 signal=0
DRM_PLUGIN_PROBE STALE_REVOKE_PASS
```

The controller exits `0` and the stale child exits `113` without a signal.

## Exact receipt

```text
FEX branch: ci/drm-loadmodule-plugin-stale-revoke-20260814
head:       1ba8a4c67d58c875e78529317c8012f0693585c0
run:        31795672985
job:        94752128456
result:     success
artifact:   drm-plugin-stale-revoke-31795672985
artifact id: 9217372076
sha256:     25fde54bf30b2845a6f8f7cdbb7e17015b7fffebff838fd1fc7a26141c61bb99
```

## What this closes

For this real retained DRM callback family, the research model now covers both sides of retirement:

```text
entry before retirement + owner still active
  -> acquire execution lease
  -> physical unmap deferred
  -> callback returns
  -> last release reclaims owner generation

entry after retirement
  -> stable descriptor remains
  -> owner state denies acquire
  -> controlled revoke path (113)
```

This is the real-API equivalent of the synthetic stale-trampoline gate and confirms that descriptor lifetime must exceed target-code lifetime when native state can retain the callback address.

## Boundary

The generated resident unpacker and unloadable callback target have different OwnerIDs. The successful run leases only the callback target owner (`0x12`). This supports keeping generated-adapter lifetime and application callback-target lifetime as separate ownership classes.

The current OwnerID prototype remains research code. Destructive memory operations that can remove or replace an actively leased owner still require memory-layer arbitration.
