# Real generated Vulkan — callback descriptor + PFN lifetime integration

Date: 2026-08-14

## Scope

This run integrates the preferred immutable host-trampoline / atomic callback-descriptor design with the proven dynamic-PFN lifetime candidate and executes both against FEX's real generated Vulkan guest/host thunk pair.

Reviewed FEX source: `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned-FEX carrier branch: `ci/thunk-callback-descriptor-20260814`.

Carrier commit: `acb16b0cc91bf615a51a2f02cd10d235f8b48c63`.

Workflow run: `31774384886`.

Artifact: `vulkan-pfn-callback-descriptor-31774384886`.

Artifact digest:

```text
sha256:a20d95f99ba572af5b426bda1e5919230de9c3eba35578ec730c512e3a2cac1d
```

No upstream FEX interaction was made.

## Matrix

```text
hold=0
close=139
reload=0
```

The meaning matches the real Vulkan PFN candidate gate:

- `hold`: extra DSO ref keeps generation 1 live and PFN remains callable;
- `close`: final owner retirement makes stale PFN a controlled revoked synthetic H and stale use exits 139;
- `reload`: old Vulkan mappings are reserved, generation 2 is forced to a new guest base, H is reactivated against T2, and the real Vulkan PFN call returns successfully.

## Callback descriptor evidence

The real generated Vulkan guest constructor creates three host-callable trampolines for the X11 setup path. Instead of embedding mutable guest-lifetime state directly in escaped executable trampoline bytes, each trampoline references an FEX-owned descriptor.

Generation 1 creates:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e000 descriptor=<d0> unpacker=0x7ffff7ea2380 target=0x7ffff7e43100
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e030 descriptor=<d1> unpacker=0x7ffff7ead050 target=0x7ffff7e43110
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e060 descriptor=<d2> unpacker=0x7ffff7ea23a0 target=0x7ffff7e43130
```

On final generation-1 unload, all three descriptors are retired while their guest unpackers still belong to the outgoing Vulkan wrapper range:

```text
DIAG_CALLBACK_DESCRIPTOR_RETIRE ... unpacker=0x7ffff7ea23a0 ... range=0x7ffff7e75000+0x4c000
DIAG_CALLBACK_DESCRIPTOR_RETIRE ... unpacker=0x7ffff7ead050 ... range=0x7ffff7e75000+0x4c000
DIAG_CALLBACK_DESCRIPTOR_RETIRE ... unpacker=0x7ffff7ea2380 ... range=0x7ffff7e75000+0x4c000
```

The escaped host trampoline bytes are not rewritten. The descriptor state is the revocable lifetime object.

Generation 2 is forced to a different guest base and allocates fresh descriptors/trampolines whose guest unpackers are in the new wrapper generation:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e090 descriptor=<d3> unpacker=0x7ffff7671380 target=0x7ffff7e43100
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e0c0 descriptor=<d4> unpacker=0x7ffff767c050 target=0x7ffff7e43110
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7e3e0f0 descriptor=<d5> unpacker=0x7ffff76713a0 target=0x7ffff7e43130
```

These generation-2 descriptors are independently retired on final close.

## Dynamic Vulkan PFN evidence in the same binary

The same run also executes the real dynamic PFN path.

Generation 1:

```text
H     = 0x7ffff76c80f4
gipa1 = 0x7ffff7ea22b0
T1    = 0x7ffff7ea4400
```

Before close:

```text
PROBE return where=before-close result=0 version=0x403113
```

Final generation-1 retirement:

```text
DIAG_MULTI_DROP H=0x7ffff76c80f4 T=0x7ffff7ea4400 ...
DIAG_MULTI_RETIRE H=0x7ffff76c80f4 OLD=0x7ffff7ea4400 NEW=0
DIAG_REVOKED_H_INSTALL H=0x7ffff76c80f4
DIAG_LOCKED_RETIRE H=0x7ffff76c80f4 ...
```

Stale H remains synthetic and compiles its revoked path:

```text
DIAG_REVOKED_H_COMPILE H=0x7ffff76c80f4
```

For reload, all old Vulkan mappings are reserved. Generation 2 moves:

```text
gipa2 = 0x7ffff76712b0
T2    = 0x7ffff7673400
H     = 0x7ffff76c80f4
same-pfn=1
```

The same H is reactivated against T2:

```text
DIAG_REVOKED_H_ACTIVATE H=0x7ffff76c80f4 T=0x7ffff7673400 ...
DIAG_MULTI_ACTIVE H=0x7ffff76c80f4 T=0x7ffff7673400
```

The real Vulkan call then succeeds:

```text
PROBE return where=after-reload-new-pfn result=0 version=0x403113
```

## Meaning

This closes an integration gap between the previously separate preferred mechanisms:

- owner-aware dynamic-PFN retirement/revocation/rebind;
- callback lifetime represented by immutable escaped host trampolines and process-lived revocable descriptors.

Both mechanisms coexist and execute on the real generated Vulkan wrapper, including Vulkan's X11 constructor callback setup and forced moved wrapper reload.

The descriptor design is therefore preferred over the older diagnostic that mutated `TrampolineInstanceInfo` fields in place.

## Important limitation

This run does not close the already-selected execution race.

`TWENTIETH_PASS_INFLIGHT_SELECTION_RUNTIME.md` proves that a thread can retain an already-selected old-generation host-code pointer after future H lookup state has been retired and after the guest owner has been physically unmapped. The descriptor design fixes callback state ownership; the H→T physical-unmap path still needs execution draining, a hazard/lease protocol, a process-resident executable bridge, or a resident wrapper policy.

For that reason this integrated candidate is a strong generation-rebind and callback-lifetime proof, not a complete physical-reclamation repair.

All source changes are diagnostic/research code in owned repositories. FEX contribution policy requires any upstream implementation to be independently derived and written by a human.