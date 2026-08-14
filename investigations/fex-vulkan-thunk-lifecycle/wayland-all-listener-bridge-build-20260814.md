# Wayland generalized resident listener bridge build — 2026-08-14

## Result

Workflow run `31789560955` completed successfully on ARM64.

The transform moved every currently recognized **64-bit** typed Wayland listener allocation site behind one per-library resident allocator:

```
FEXWaylandAllocateResidentListener(callback, normalized_signature)
```

Transform receipt:

```
Wayland resident listener diagnostic applied to 41 typed allocation sites
```

The unloadable wrapper continues to own:

- protocol message parsing / normalization;
- listener table allocation and proxy bookkeeping;
- normal Wayland API entrypoints.

The resident companion owns the finite typed callback-unpacker dispatcher used when creating FEX host-to-guest trampolines.

## ELF boundary

The ordinary wrapper remains unloadable and has a dynamic dependency on the companion:

```
NEEDED libfex-wayland-client-bridge.so
SONAME libwayland-client.so.0.20.0
```

It has no `DF_1_NODELETE` flag.

The companion has:

```
SONAME libfex-wayland-client-bridge.so
FLAGS_1 NODELETE
```

## Size receipt

`size` on the two guest DSOs:

```
   text   data  bss    dec    hex  filename
  21368   1000    8  22376   5768  libwayland-client-guest.so
  10713    872    8  11593   2d49  libfex-wayland-client-bridge.so
```

This is the intended ownership granularity: the resident code is a small companion rather than the whole Wayland wrapper.

## Relationship to the runtime proof

The earlier synchronous retained-listener run `31788266927` already proved the causal lifetime behavior for protocol signature `"u"`:

- exact callback works before unload in both arms;
- local wrapper-owned unpacker exits 139 after physical unload + moved reload;
- resident unpacker delivers callback 42 after the same moved reload without re-registering the listener.

Run `31789560955` is a **build/generalization** gate. It proves the existing 64-bit finite signature set can be moved into the per-library resident dispatcher without compile/link breakage. It does not by itself re-run every protocol signature dynamically.

## Remaining Wayland scope

The special `wl_array` callback relocation path used for 32-bit guests is still separate. Do not treat this 64-bit build as validation of 32-bit `a` / `iia` / `uoa` callback relocation semantics.

Next useful Wayland runtime check is to rerun the already-proven synchronous `"u"` retained-registration-only carrier using this full 41-signature resident dispatcher instead of the narrow one-signature prototype. That validates the generalization did not disturb the known-good lifetime path.
