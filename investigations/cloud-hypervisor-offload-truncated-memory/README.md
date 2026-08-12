# Cloud Hypervisor offload snapshot — truncated memory artifact

State: EXECUTION IN PROGRESS
Parent context: #555
Exact source: `cloud-hypervisor/cloud-hypervisor@1af93ac7035cda77cd87b0c18b1134ebb0928052`
External-contact state: false; none occurred

## Question

Can offload restore silently accept a `memory-<slot>` artifact whose file length is shorter than the memory size declared by the migration config?

## Source observation

`offload_daemon::create_memfd_with_contents()` pre-sizes the destination memfd to the configured memory range and then calls `vmm::sparse::copy_region()` for that configured length.

The sparse copy path uses `SEEK_DATA` / `SEEK_HOLE`. `SEEK_DATA` returning `ENXIO` means "no more data" and is treated as the remainder being a hole. There is no source-file-length check before the copy.

Therefore a source file whose EOF is before the configured range end can be indistinguishable from a sparse zero tail: the destination memfd was already sized, so its uncopied tail reads back as zero.

On-demand restore independently opens the same disk artifact without an upfront length check and discovers truncation only if a later page fault requests bytes beyond EOF.

## Discriminator

Create a 4 KiB snapshot memory file filled with `0xa5`, then ask the exact current restore helper to materialize an 8 KiB memory range.

Baseline prediction:

```text
source length = 4096
configured size = 8192
create_memfd_with_contents() = Ok
memfd[0..] = a5
memfd[4096..] = 00
```

This test does not rely on OOM, KVM, a guest, or filesystem corruption. It directly distinguishes "short artifact" from a legitimate 8 KiB sparse file, whose logical file length would still be 8192.

## Candidate boundary

Before either eager or on-demand restore uses a memory artifact, require:

```text
metadata.len() >= configured slot size
```

A sparse file with holes remains valid because holes do not reduce logical file length. A physically truncated artifact fails before any state is sent to Cloud Hypervisor.

Keep this separate from #555's multi-file generation-publication problem. A stale memory file can be full-sized and therefore pass this check; generation identity still needs its own publication invariant.
