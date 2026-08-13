# Fifteenth pass: escaped host->guest callback can be tombstoned in place

Status: internal Fieldwork evidence for issue #672. FEX upstream remains read-only.

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.

Owned carrier: `teamleaderleo/FEX:ci/callback-tombstone-diagnostic-20260814`.

Run: `31745060252`.

Artifact: `thunk-callback-tombstone-31745060252`.

Artifact digest: `sha256:6d26f3c77d6d7cd27107ce6402637fd2f4f93299c964920294d5be62d5527c51`.

## Question

FEX host->guest callback trampolines are process-owned executable allocations. Their embedded record contains:

```text
HostPacker
CallCallback
GuestUnpacker
GuestTarget
```

The trampoline address may escape into a native host library and remain there after the guest DSO containing `GuestUnpacker` / `GuestTarget` is unloaded.

Can FEX keep that escaped host pointer itself valid while revoking its ability to enter dead guest code?

## Diagnostic

The experiment adds owner-range retirement for `GuestcallToHostTrampoline` entries.

Before a guest range is physically unmapped, every cached host trampoline whose `GuestUnpacker` or `GuestTarget` falls inside that range is modified in place:

```text
CallCallback  -> FEX-owned revoked callback handler
GuestUnpacker -> 0
GuestTarget   -> 0
```

The old cache key is erased as well, so a later guest generation is free to allocate a fresh trampoline even if guest addresses are reused.

The diagnostic revoked handler terminates the child probe with exit code `113`. This is intentionally a visible mechanism marker, not proposed production behavior.

## Runtime receipt

Generation 1 works before unload:

```text
pre-unload host->guest callback  rv=10053 want=10053
```

Before the first guest DSO disappears, FEX records:

```text
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c000 \
  unpacker=0x7ffff7da2190 target=0x7ffff7da2170 \
  range=0x7ffff7da1000+0x5000
```

The old guest target and unpacker are then unmapped. Generation 2 is forced to a different guest base.

Using the retained first-generation host callback pointer no longer produces a guest-code SIGSEGV:

```text
DIAG_CALLBACK_REVOKED invoked
child retained callback reload    exit=113
```

After generation 2 creates a new/current callback, the original first-generation callback remains revoked:

```text
DIAG_CALLBACK_REVOKED invoked
child first callback after new    exit=113
```

The generation-2 callback itself remains healthy:

```text
fresh/current callback             rv=10010053 want=10010053
child current callback after new   rv=10010093
child current callback after new   exit=0
```

The second generation receives a distinct FEX host trampoline allocation and is tombstoned at its own later unload:

```text
DIAG_CALLBACK_TOMBSTONE trampoline=0x7ffff7d7c030 \
  unpacker=0x7ffff7d78190 target=0x7ffff7d78170 \
  range=0x7ffff7d77000+0x5000
```

The dynamic-PFN route was intentionally untouched in this experiment and therefore remains stale:

```text
child retained Link after reload  signal=11
child Link after re-register      signal=11
```

That separation is useful: callback tombstoning fixes only the host->guest stale-address class.

## Why in-place tombstoning works

The host trampoline does not bake the guest target into the branch instruction itself. It puts a pointer to its embedded `GuestcallInfo` record into the custom ABI register and jumps to `HostPacker`.

The host-side callback packer reads that record on every invocation and performs:

```text
CallCallback(GuestUnpacker, GuestTarget, packed_args)
```

Therefore FEX can revoke an already-escaped host trampoline by mutating FEX-owned record data without changing the host pointer already stored by a native library.

## What this proves

- host->guest callback lifetime is an independent real stale-address class;
- an escaped FEX host trampoline pointer does not need to be withdrawn from native code to be made safe;
- mutable FEX-owned indirection is sufficient to prevent that pointer from entering retired guest code;
- a new guest generation can allocate and use a current callback while the old pointer remains revoked;
- callback repair is separate from dynamic-PFN CustomIR repair.

## What this does not prove

The diagnostic uses process exit `113` as a clear tombstone marker. A production implementation needs a semantic policy for a callback invoked after its guest owner is gone.

Possible policies depend on ownership:

- deterministic fatal/error for an invalid callback use;
- keeping the guest owner alive while the host legitimately retains the callback;
- explicit host-side deregistration/reference tracking;
- a stable indirection object with a revocation state.

Blindly rebinding an arbitrary old callback to a new guest callback solely because their signatures match would be wrong: signature compatibility is not callback identity.

Concurrency is also not solved by this single-thread diagnostic. Mutating a trampoline record while another host thread is executing through it needs atomic state and/or a quiescence protocol.

## Next discriminator

The next callback-specific test should reload at the same guest addresses when possible. Because the tombstoned `{GuestUnpacker, GuestTarget}` key is erased, a same-address generation must allocate a fresh host trampoline rather than retrieving the old tombstoned instance. That tests the address-reuse/ABA case directly.
