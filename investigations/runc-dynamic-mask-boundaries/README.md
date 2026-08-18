# runc dynamic CPU and NUMA mask boundaries

Tracks Linux Fieldwork issues #447 and #448.

## In simple words

Two adjacent boundaries were found while reviewing runc's move from fixed 1,024-bit masks to `unix.CPUSetDynamic`:

1. runc accepts CPU/NUMA ID `65536`, but its reset-affinity mask uses that value as an exclusive constructor bound and omits the accepted top bit;
2. `golang.org/x/sys/unix.SetMemPolicyDynamic` passes a dynamic mask's byte size as Linux's `maxnode` argument, while the kernel interprets `maxnode` as a bit count.

This directory retains a small discriminator that does not require a 65,537-CPU machine or a multi-node runner to establish the argument and constructor boundaries.

## Exact source boundary

- runc: `opencontainers/runc@0c87c02ff02123f1bc2cd1b3f850f94e5b8de983`;
- dynamic-mask change: `daf934fefc0b2529f2bc7feb4d3539101642b762`;
- reset-mask reuse change: `c55649b75ea77bfee5a7d11d6c8e2ef3a9e73547`;
- runc dependency: `golang.org/x/sys v0.47.0`;
- x/sys source inspected at `9e7e939dcafac07e8ab4cffa6e5fc74908413f00` and current default source;
- Linux kernel source inspected at `torvalds/linux@c21bb4193868a8de71fc4693fa741e195fdf5d86`.

No matching runc or x/sys issue or pull request was found by the duplicate searches recorded in #447 and #448.

## Probe map

`main.go` has four modes:

- `constructor` compares `NewCPUSet(65536)` with `NewCPUSet(65537)` and requires only the latter to contain bit `65536`;
- `wrapper` calls `unix.SetMemPolicyDynamic` with a one-word mask containing node bit 7;
- `raw` calls `SYS_SET_MEMPOLICY` with the same mask and an explicit bit-capacity argument;
- `all` runs the three controls without syscall tracing.

The hosted workflow runs the wrapper and raw controls under `strace -e set_mempolicy`, retains both traces, records architecture and tool identities, verifies a clean checkout, and publishes a checksummed artifact.

## Distinguishing outcomes

### Constructor boundary

Current expected output:

```text
exclusive_has_max=false inclusive_has_max=true
```

A future result where `exclusive_has_max=true` means the x/sys constructor contract or representation changed and the runc interpretation must be re-reviewed.

### NUMA syscall argument

On a 64-bit runner with one dynamic mask word:

- the x/sys wrapper is expected to issue `set_mempolicy(..., maxnode=8)` because `CPUSetDynamic.size()` returns bytes;
- the raw control issues `set_mempolicy(..., maxnode=64)` using the mask capacity in bits.

The syscall may return `EINVAL` on both paths when node 7 is not present or allowed. That status is not the discriminator. The retained third argument is.

## Evidence limits

- this first probe proves constructor and syscall-argument ownership, not a production topology's final allocation behavior;
- native high-node behavior remains a later capability-dependent matrix;
- Linux's historical internal decrement of `maxnode` should be handled explicitly in any eventual dependency repair test;
- this branch contains no runc product patch.

## Next branches

1. Tiny runc owned-fork candidate for #447: allocate the reset mask with `configs.MaxCPU + 1` and add a source-level top-bit guard.
2. For #448, use the hosted trace to choose between an x/sys dependency repair and a temporary runc raw-syscall workaround.
3. Add 32-bit execution if current hosted tooling can run the probe without weakening exact dependency identity.

## Authority

Internal Linux Fieldwork only. No upstream issue, pull request, review, comment, reaction, email, or other external contact is authorized or made.
