# Zero-progress refinement — truncated migration memory payload

Updated: 2026-08-11
Owning issue: #580
Cloud Hypervisor source: `915d359f97475b1a39d8561f8db514da9e692d19`
Pinned dependency: `vm-memory = "0.18.0"`
External-contact state: false; none occurred

## TL;DR

The current receive-memory retry loop has a deterministic zero-progress failure mode in addition to the open-but-idle cancellation problem already mapped in this investigation.

`receive_memory_ranges()` repeatedly calls `GuestMemoryBackend::read_volatile_from()` and advances `offset` by the returned byte count. It checks only whether `offset == range.length`. It does not handle `bytes_read == 0`.

The pinned rust-vmm `vm-memory` 0.18.0 contract permits exactly that result: `ReadVolatile::read_volatile()` is defined to behave like `std::io::Read::read()`, and the raw-fd implementation returns a successful `0` directly when `libc::read()` returns EOF. `GuestMemoryBackend::read_volatile_from()` sums the per-slice byte counts and does not convert zero progress to an error. The separate `read_exact_volatile_from()` helper is the API that converts zero progress into `UnexpectedEof`.

Therefore a truncated memory payload whose peer closes can leave Cloud Hypervisor looping with `offset` unchanged instead of reporting an incomplete migration receive.

## Exact source chain

Cloud Hypervisor workspace:

```text
vm-memory = "0.18.0"
```

Cloud Hypervisor `vmm/src/migration/transport.rs`:

```text
loop {
    bytes_read = mem.read_volatile_from(...)?
    offset += bytes_read
    if offset == range.length {
        break
    }
}
```

rust-vmm/vm-memory `v0.18.0`, `GuestMemoryBackend::read_volatile_from()`:

```text
get_slices(...)
    .try_fold(0, |acc, slice| acc + slice.read_volatile_from(...)?)
```

rust-vmm/vm-memory `v0.18.0`, `VolatileSlice::read_volatile_from()`:

```text
src.read_volatile(...)
```

rust-vmm/vm-memory `v0.18.0`, raw-fd `ReadVolatile`:

```text
bytes_read = libc::read(...)
bytes_read < 0 -> error
otherwise -> Ok(bytes_read)
```

`0` is therefore returned as successful zero progress. The trait documentation explicitly requires behavior identical to `Read::read()`.

## Smallest executable discriminator

A no-guest unit fixture should call the current receive path with:

1. a valid `Command::Memory` request and range table;
2. a declared nonzero memory payload;
3. fewer payload bytes than declared;
4. peer socket closed after the short payload.

Run the target call in a child thread/process under a harness deadline so the test harness itself cannot wedge.

Expected baseline:

```text
first read -> some bytes
EOF read   -> Ok(0)
offset     -> unchanged
loop       -> repeats indefinitely
```

Controls:

- exact payload length -> function returns `Ok(())`;
- malformed range table -> ordinary parse error;
- short payload with a candidate zero-progress guard -> ordinary receive/UnexpectedEof error.

## Candidate boundary

The narrow product requirement is:

> A nonempty declared memory range must either make forward progress or return an error.

A local `bytes_read == 0` check can satisfy the truncated/EOF case without introducing a migration-wide timeout. It should return an ordinary receive error identifying an incomplete memory payload.

This does **not** solve the separate connected-but-idle case. If the peer stays open and sends no bytes, the blocking read still cannot observe the receiver kill event. Keep abort-aware cancellation as a distinct second discriminator under #580.

## Sibling send path

`send_memory_ranges()` also has a manual progress loop, but its current `GuestMemoryBackend::write_volatile_to()` implementation uses `write_all_volatile_to()` per guest-memory slice, which already converts zero writes to `WriteZero` before returning. Do not broaden the receive finding into a symmetric sender zero-progress claim without separate evidence.

## Evidence boundary

This is stronger than a generic I/O assumption: it is established against the exact dependency version Cloud Hypervisor declares and the exact current receive loop. It still needs an executable Cloud Hypervisor fixture before promotion to a candidate patch.

No upstream interaction has occurred.
