# Cloud Hypervisor — async block bounce OOM reachability check

Updated: 2026-08-13
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: NEGATIVE — proposed guest-triggered buffered-bounce OOM is not reachable through the examined async block path

## Question

Could a malicious guest inflate a virtio-blk descriptor chain to nearly 4 GiB of cumulative, overlapping valid buffers and force the async buffered block path through `OwnedIoBuffer::new(..., alignment=0)`, where the ordinary `Vec` allocation is not fallible?

## What looked suspicious

`Request::data_len()` sums guest data-descriptor lengths, and `OwnedIoBufferStorage::new()` contains:

```rust
if alignment <= 1 {
    return Ok(Self::Vec(vec![0; len]));
}
```

A legal 32,768-entry queue can describe 32,766 data segments. Per-descriptor range validation does not require those ranges to be distinct, so a chain can have a very large cumulative length while repeatedly referencing a much smaller valid guest-memory range.

## Reachability stop condition

The missing link is decisive. `Request::build_data_operation()` first calls:

```rust
if self.guest_memory_is_aligned(&mem, alignment)? {
    let target = GuestMemoryTarget::new(mem, &self.data_descriptors)?;
    ...
}
```

and `guest_memory_is_aligned()` begins:

```rust
if alignment <= 1 {
    return Ok(true);
}
```

Buffered raw disks use alignment `0`. Therefore they take the direct guest-memory operation and **do not call `OwnedIoBuffer::new()` at all**.

When direct I/O supplies alignment greater than one and a guest buffer is unaligned, the bounce path is reachable, but it selects the explicitly aligned allocation branch. That branch already checks `alloc_zeroed()` for null and returns `io::ErrorKind::OutOfMemory` normally.

## Disposition

**Do not promote this as a guest-triggered Cloud Hypervisor DoS.**

The `Vec` allocation seam may still be worth ordinary robustness cleanup if another caller can reach it with attacker-sized input, but the specific malicious virtio-blk chain investigated here does not reach it in buffered async I/O, and the direct-I/O bounce branch is already fallible.

No hosted product execution is warranted for this claim because exact-source control-flow inspection closes the proposed guest-reachability chain before the suspected allocation owner.
