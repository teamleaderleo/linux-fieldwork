# Twenty-seventh pass — immutable callback trampoline + atomic descriptor runtime

## Scope

The earlier callback tombstone proved that an escaped host trampoline can remain at a stable native address while its guest destination is revoked. That diagnostic mutated several raw fields inside the trampoline instance record, which is mechanically effective but leaves an avoidable data-race concern if native code reads those fields concurrently.

This checkpoint prototypes a cleaner representation:

```text
escaped host trampoline C   (immutable after publication)
  -> generated host packer
  -> stable FEX dispatcher
  -> host-owned descriptor D
       atomic state = LIVE | REVOKED
       immutable GuestUnpacker
       immutable GuestTarget
```

Source under test: FEX `71afe476751deac24adabd1adb575fd2337b6e0a`.
Owned-FEX branch: `ci/thunk-callback-descriptor-20260814`.
Carrier commit: `ce870ff6272c261b49ffb27114b16ebb8cf0780c`.
Workflow run: `31772219765`.
Artifact: `9208621504`, `thunk-callback-descriptor-31772219765`.

## How it fits the existing generated ABI

No generated Host.h callback ABI change is required for this prototype.

The existing host packer already calls the embedded FEX callback dispatcher with three values. Instead of storing the raw guest unpacker in the first field, the trampoline stores the stable host descriptor pointer there and leaves the second embedded target field unused.

The FEX dispatcher receives the descriptor pointer, performs an acquire load of its state, then reads the immutable real guest unpacker/target from the descriptor before entering guest code.

Because the published trampoline fields never change, native host code and FEX do not race over a partially updated `{CallCallback, GuestUnpacker, GuestTarget}` tuple.

## Forced-different reload

Generation 1 allocates one trampoline and descriptor:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7d7c000 descriptor=0xff948a61d000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0xff948a61d000 unpacker=0x7ffff7da2190 target=0x7ffff7da2170
```

Owner retirement performs the atomic state transition and removes the old callback cache key:

```text
DIAG_CALLBACK_DESCRIPTOR_RETIRE trampoline=0x7ffff7d7c000 descriptor=0xff948a61d000 ...
```

The escaped generation-1 host pointer remains executable but reaches the revoked descriptor path:

```text
DIAG_CALLBACK_DESCRIPTOR_REVOKED descriptor=0xff948a61d000
child retained callback reload    exit=113
```

Generation 2 receives a fresh trampoline and fresh descriptor:

```text
DIAG_CALLBACK_DESCRIPTOR_CREATE trampoline=0x7ffff7d7c030 descriptor=0xff948a61d020 unpacker=0x7ffff7d78190 target=0x7ffff7d78170
DIAG_CALLBACK_DESCRIPTOR_LIVE descriptor=0xff948a61d020 unpacker=0x7ffff7d78190 target=0x7ffff7d78170
```

The current callback works:

```text
fresh/current callback            rv=10010053 want=10010053
child current callback after new  rv=10010093
child current callback after new  exit=0
```

The complete force case exits 0.

## Same-address ABA

The guest loader reuses the exact same numeric `GuestUnpacker` / `GuestTarget` addresses for generation 2.

The old descriptor remains revoked:

```text
DIAG_CALLBACK_DESCRIPTOR_REVOKED descriptor=0xffa4e701d000
child retained callback reload    exit=113
```

Because retirement erased the old `{GuestUnpacker, GuestTarget}` cache key, lookup allocates a new host trampoline/descriptor even though the guest numeric addresses are identical:

```text
old trampoline=0x7ffff7d7c000 descriptor=0xffa4e701d000
new trampoline=0x7ffff7d7c030 descriptor=0xffa4e701d020
```

The new descriptor is LIVE and current callback execution succeeds. The complete ABA case exits 0.

## Other integrated controls

The same FEX build preserves the dynamic-PFN lifetime behavior:

```text
thread-cache case exit=0
multi-owner promotion case exit=0
```

So replacing mutable callback tombstoning with stable descriptor revocation does not regress exact all-thread H retirement or same-H compatible owner promotion in the reduced matrix.

## Preferred callback direction

This descriptor model supersedes the mutable raw-field tombstone as the preferred research architecture for host->guest callbacks.

Retirement becomes:

```text
lock owner registry
  -> descriptor.state.store(REVOKED, release)
  -> erase retired callback cache key
```

Invocation becomes:

```text
state = descriptor.state.load(acquire)
if REVOKED:
    deterministic revoked callback behavior
else:
    enter immutable GuestUnpacker / GuestTarget
```

The remaining concurrency question is an invocation that already loaded LIVE before retirement stores REVOKED. If FEX needs to guarantee physical unmap against legal asynchronous host callbacks, the descriptor is now a natural place to add an execution lease/refcount or draining state. The current runtime proof establishes stable revocation for future invocations, not that final drain rule.

No upstream FEX interaction was performed.