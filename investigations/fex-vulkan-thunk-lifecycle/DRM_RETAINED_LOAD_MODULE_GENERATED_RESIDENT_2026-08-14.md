# Generated DRM retained `load_module` callback through resident bridge

Date: 2026-08-14
Status: successful hosted ARM64 proof
Scope: owned FEX/fieldwork surfaces only

## Result

The current thunkgen callback-member research can carry a real libdrm callback that is retained beyond the setter call through a process-resident generated guest bridge while the ordinary libdrm guest wrapper physically unloads and reloads elsewhere.

Exact receipt:

```text
branch:   ci/agent-b-drm-serverinfo-loadmodule-resident-20260814
head:     696d6814fffce381ab2faf7fca8ec67c0901bdb9
run:      31791873613
job:      94740381762
result:   success
artifact: agent-b-drm-serverinfo-loadmodule-resident-31791873613
id:       9215907428
sha256:   5e876fbc0a37a7d89392c53d8123391acbc69e5191e2b56e84253e347b5a11ec
```

The artifact matrix is:

```text
native_precondition=0
wrapper_owned_unpacker_reference=139
handwritten_resident_reference=0
generated_loadmodule_resident=0
OUTCOME=generated_loadmodule_conversion_survived_retained_moved_reload
```

## What is generated

The research generator annotates:

```cpp
struct fex_gen_config<&drmServerInfo::load_module> : fexgen::callback_member {};
```

The guest side copies the callback-bearing input structure, replacing only the typed callback member with a generated host trampoline rather than mutating the caller's input object.

The generated host side finalizes the callback-member trampoline before libdrm consumes the converted structure.

The normal generated libdrm guest output exposes four callback signatures and the derived resident bridge contains the same four-signature set:

```text
normal_callback_signatures=4
bridge_callback_signatures=4
```

The ordinary wrapper redirects generated callback-trampoline allocation to the resident companion:

```text
#define AllocateHostTrampolineForGuestFunction FEXAllocateResidentHostTrampolineForGuestFunction
```

## ELF ownership

The generated bridge is a separate guest ELF:

```text
SONAME: libfex-drm-bridge.so
FLAGS_1: NODELETE
```

The ordinary libdrm guest wrapper remains unloadable and has an ELF dependency on the bridge:

```text
NEEDED: libfex-drm-bridge.so
SONAME: libdrm.so.2
wrapper NODELETE: no
```

The bridge extraction step reports:

```text
extracted 4 resident bridge signatures for libdrm
```

## Retained containing object

`drmServerInfo` is a stronger lifetime case than synchronous `drmEventContext`: native libdrm keeps the supplied containing structure beyond the setter call.

The host research wrapper therefore keeps its own converted structure:

```cpp
static void fexfn_impl_libdrm_drmSetServerInfo(drmServerInfoPtr info) {
  if (!info) {
    fexldr_ptr_libdrm_drmSetServerInfo(nullptr);
    return;
  }

  retained_server_info = *info;
  fexldr_ptr_libdrm_drmSetServerInfo(&retained_server_info);
}
```

This reinforces the generator design split:

```text
callback_member
  -> how the callable crosses ISA and gets a resident generated unpacker

retained containing object
  -> who owns the converted aggregate after the thunk call returns
```

Those are independent semantics and should remain separate metadata/contracts.

## Moved-wrapper runtime proof

Generation 1 records five libdrm wrapper ranges and registers the retained callback:

```text
GEN1 ... callback=0x5641350e6a10 ranges=5
MARK set-info-return count=0
```

The wrapper is then closed and the old setter address is confirmed unmapped:

```text
MARK close1-return old_set_mapped=0
```

The old ranges are deliberately reserved so generation 2 must load elsewhere:

```text
GEN2 ... moved=1
```

Without re-registering `drmServerInfo`, a generation-2 libdrm operation triggers the previously retained callback:

```text
MARK open2-enter retained-registration-only
DRM_SERVER_CALLBACK count=1 name=fex-intentionally-missing-drm-driver
MARK open2-return fd=-1 callbacks=1
```

So the callback conversion and resident generated unpacker survive a real physical wrapper generation transition.

## Evidence boundary

This proves generated **bridge/unpacker** lifetime for a real callback retained by libdrm. The test callback target itself remains valid for the duration of the process.

It therefore complements rather than replaces the callback owner-generation lease work. A separately unloadable guest callback-target DSO still needs retirement + execution-lease semantics even when the generated unpacker is resident.

That split is desirable:

```text
resident generated bridge
  -> process-lifetime callback unpacker

actual application callback target
  -> application mapping/load-generation lifetime
```

## Next integration discriminator

Use this DRM path after the OwnerID-backed synthetic callback lease is green:

1. put the actual guest `load_module` target in a separately unloadable guest plugin DSO;
2. keep the generated resident DRM unpacker and retained native `drmServerInfo` state;
3. trigger callback execution while the plugin generation retires;
4. require future old callback entry to revoke and already-entered execution to hold the plugin owner lease;
5. reload the plugin, preferably with forced address movement and then a same-address ABA variant.

That would combine the two independently proven halves of the proposed architecture on a real retained-callback API.
