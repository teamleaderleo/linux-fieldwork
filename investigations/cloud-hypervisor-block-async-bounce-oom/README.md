# Cloud Hypervisor — guest-sized async block bounce allocation can abort the VMM

Updated: 2026-08-13
Fieldwork base: `fee128d20bbcdc99bb62e75b3575247356d64a16`
Exact Cloud Hypervisor source: `1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; upstream remains read-only
State: STAGED

## Security-oriented question

Can a malicious guest submit a valid virtio-blk descriptor chain whose individually valid, overlapping buffers sum to a very large request, causing Cloud Hypervisor's async buffered block path to make an infallible `vec![0; len]` host allocation and abort the entire VMM on allocation failure?

This is a host-process availability boundary, not a guest escape claim.

## Exact-current source chain

`block/src/io/request.rs` stores every validated data descriptor and computes `data_len()` as the sum of their lengths. `build_data_operation()` passes that sum to `OwnedIoBuffer::new(self.data_len(), alignment)` when it needs a bounce buffer.

`block/src/io/async_io/owned_io_buffer.rs` currently does:

```rust
if alignment <= 1 {
    return Ok(Self::Vec(vec![0; len]));
}
```

The function returns `io::Result`, but ordinary `Vec` allocation failure uses Rust's allocation-error path and aborts the process rather than producing that `Result` error.

The aligned branch is already different: it calls `alloc_zeroed`, checks for null, and returns `io::ErrorKind::OutOfMemory`.

Buffered raw disks use `AlignedFile::new(..., direct_io=false)`, whose alignment is `0`, so they select the `Vec` branch.

## Guest-shaped upper bound

Cloud Hypervisor validates virtio queue size as a power of two up to 32,768. The block device advertises `seg_max = queue_size - 2`.

Pinned `virtio-queue 0.18.0` bounds a descriptor chain by queue size and stops a chain whose cumulative descriptor byte length would overflow `u32`, i.e. chains below 4 GiB remain representable.

Cloud Hypervisor's checked-descriptor layer validates each translated `(addr, len)` against guest RAM independently. It does not require different descriptors to reference distinct ranges.

A concrete shape is therefore:

```text
queue descriptors        = 32768
header                    = 1 descriptor
data                     = 32766 descriptors
status                    = 1 descriptor
per-data descriptor len   = 131064 bytes (< 128 KiB)
data sum                  = 4,294,443,024 bytes (~4 GiB)
```

All data descriptors can refer to the same valid guest range. Header + data + status remain below the virtio `u32` cumulative-byte ceiling.

## Baseline discriminator

Under a controlled address-space limit, call the exact `OwnedIoBuffer::new(4_294_443_024, 0)` production allocation seam.

Expected exact-current result: process allocation failure / abort before an `io::Result` can be returned.

Negative control: the same huge length with alignment 512 follows the already-fallible aligned allocation and returns `OutOfMemory` without aborting.

Small ordinary allocation remains successful.

## Minimum candidate

For `alignment <= 1`, reserve the `Vec` capacity with `try_reserve_exact(len)` and map failure to `io::ErrorKind::OutOfMemory`, then zero-initialize within the already-reserved capacity.

Do not alter async request semantics, descriptor limits, direct-I/O alignment, or the aligned allocation path.

## Gates

- exact source pin;
- exact pinned `virtio-queue 0.18.0` cumulative-chain source check;
- concrete 32,768-descriptor guest-shape arithmetic receipt;
- small allocation control;
- huge aligned-allocation negative control returns an error;
- huge buffered allocation baseline abort under fixed `RLIMIT_AS`;
- restore exact source;
- candidate turns the same huge buffered allocation into a normal error;
- full `block` library tests;
- dependent `virtio-devices` compile check;
- Clippy, nightly rustfmt, `git diff --check`;
- complete candidate-only diff hash.
