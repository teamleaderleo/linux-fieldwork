# Deep dive

## Bounded question

Does Debian trixie `util-linux 2.41-5` still expose the upstream cpuset output-ownership defect, and does the canonical free-then-NULL correction form a suitable stable-package backport?

## Mechanism

`ul_path_cpuparse()` publishes an allocated cpuset through a caller-owned pointer. On malformed input, affected source frees the allocation and returns an error while leaving the pointer value in the caller's slot.

`lscpu` reads several masks through this helper. The `online` read stores directly into `cxt->online`; NUMA reads store into `cxt->nodemaps[]`. Final cleanup frees `cxt->present`, `cxt->online`, and later every nodemap. Heap reuse decides which later free exposes the stale address, so the public reports can surface in cache or NUMA cleanup even though shared `lib/path.c` creates the defect.

Canonical commit `4581ede...` changes the error path to:

```c
if (rc) {
        cpuset_free(*set);
        *set = NULL;
}
```

The parser status and success path remain unchanged.

## Actual trixie reproduction

A deterministic sysroot sets:

```text
kernel_max = 15
possible = 0-15
present = 0-15
online = 0-15              # valid control
node0/cpumap = 0000ffff
```

The failing mutation replaces only `online` with `5,12-%`.

Installed Debian trixie `lscpu 2.41-5`:

- valid text: 0;
- valid JSON: 0 and parseable JSON;
- malformed text: 134 with `free(): double free detected in tcache 2`;
- malformed JSON: 134 with the same allocator diagnostic.

The matrix repeated from clean temporary directories with byte-identical receipts.

## Allocator-size discriminator

The same malformed logical input can exit 0 when `kernel_max` changes because allocation size changes heap reuse. A bounded sweep produced both aborting and clean cases; behavior was non-monotonic. This is a losing control, not evidence of a safe larger topology.

The regression contract therefore fixes the exact 16-CPU allocation identity and retains a larger losing control. It avoids claiming a simple CPU-count threshold.

## Approach history

### Source archaeology only

This correctly found the upstream owner and canonical fix, but package adoption remained unknown. Superseded by exact package work.

### Broad live-sysfs fixture

Copying the host CPU tree reproduced the installed trixie failure locally. In GitHub's container it encountered unreadable power attributes and failed before executing the matrix. Rejected as host-dependent.

### Deterministic minimal sysroot

Copies only `/proc/cpuinfo` and creates the bounded CPU/NUMA identities required by `lscpu`. Accepted. It reproduces the exact allocator diagnostic and avoids transient host sysfs files.

### Final-cleanup suppression

Rejected. Skipping a late free would preserve a stale pointer and leave other readers exposed.

### Parser-policy expansion

Rejected. Accepting malformed CPU-list syntax would change policy and hide the ownership defect.

## Exact Debian source result

Actions run `30690487287` retrieved exact `2.41-5` source, applied Debian's patch series, and recorded the effective `lib/path.c`. The resulting error path still frees without clearing the output.

The canonical patch applied with `--fuzz=0`; the patched package completed `dpkg-buildpackage -b -uc -us -j2`. The run stopped only when the first fixture version copied unreadable live sysfs attributes. Source, patch, and package-build stages succeeded.

## Compatibility analysis

The correction affects only ownership after an existing parse failure:

- successful parsing and output remain on the same path;
- failure status remains nonzero;
- no input syntax becomes accepted;
- the failed allocation remains freed;
- later cleanup becomes NULL-safe;
- no file, descriptor, mount, process, or package-interface contract changes.

Actual valid text and JSON candidate comparison remains a required gate.

## Debian destination

Trixie stable remains on `2.41-5`; testing and unstable moved to fixed upstream releases. The current proposed-updates queue contains no util-linux upload. A stable update would require a minimal package delta, a suitable Debian bug, a source debdiff, focused test receipts, release-team approval, and explicit authorization from the Linux Fieldwork owner.

## Remaining discriminators

1. Execute the built candidate binary against valid and malformed text/JSON fixtures.
2. Compare valid baseline and candidate output exactly or explain deterministic environmental fields.
3. Run relevant util-linux native `lscpu` tests on the patched package tree.
4. Build a proper `2.41-5+deb13u1` source package and retain the source debdiff.
5. Decide whether the bug's impact and evidence justify Debian stable-update handling.
6. Recover issue #4401's exact archive when a supported binary-download path exists.

## Evidence boundary

Established on Debian trixie amd64 and a deterministic synthetic sysroot. The public attachment, other architectures, ASan/Valgrind on the actual package, and Debian acceptance remain outside the claim.

## Reopen triggers

- Debian publishes an equivalent trixie correction;
- the queued candidate retains any abort or changes valid output;
- native tests identify an adjacent required change;
- the canonical patch stops applying to the effective package source;
- issue #397 supplies carriers for a separate cgroup-mount unit;
- external-contact authority changes.
