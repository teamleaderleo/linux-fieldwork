# Deep dive

## Question and observed failure

The bounded question is: after upstream and stable-branch adoption, does a maintained downstream still ship the affected util-linux source, and what exact contribution remains?

Affected util-linux `v2.41` publishes an allocated cpuset through `cpu_set_t **set`. On parse failure, `ul_path_cpuparse()` frees `*set` and returns an error while leaving the freed address in the caller's slot. Later ordinary `lscpu` cleanup follows that stale address. The allocator reports the final duplicate free, while shared `lib/path.c` creates the ownership defect.

The issue/index wording about an “owning cgroup mount” conflicts with every canonical linked carrier. No linked source, test, issue, or patch selects a cgroup mount. This packet follows the exact carrier mechanism: cpuset output ownership after parser failure.

## Source mechanism

Affected `v2.41` ends `ul_path_cpuparse()` with:

```c
out:
        if (rc)
                cpuset_free(*set);
        free(buf);
        return rc;
```

The sequence is:

1. `cpuset_alloc()` stores an allocation in `*set`;
2. malformed CPU-list or mask input sets a failure result;
3. the error path frees the allocation;
4. the caller-visible pointer remains non-NULL;
5. lscpu-owned structures retain the stale address;
6. later cleanup reads or frees that address again.

Canonical commit `4581ede384f22983d6155768635ce43cb5304cb0` changes the ownership state to match the completed free:

```c
out:
        if (rc) {
                cpuset_free(*set);
                *set = NULL;
        }
        free(buf);
        return rc;
```

The successful path, malformed-input policy, and failure status remain unchanged.

## Reproduction narrative

Upstream issue #3641 contains a ppc64el Valgrind trace: cpuset allocation, first free inside the parse path, invalid later reads, and a final invalid free. The reporter confirmed the patch fixed the package build failure.

Issue #4401 retains a synthetic sysfs tree with malformed online CPU content `5,12-%`. The reporter observed duplicate-free aborts on util-linux 2.40.4 and 2.41, while 2.42 did not abort.

Linux Fieldwork retains a deterministic C model to avoid deliberate undefined behavior. The baseline records the first logical free, retains the output address, and returns status 42 when later cleanup reaches it. The candidate clears the output and returns status 0 after harmless later cleanup.

Fresh 2026-08-01 execution:

```text
baseline: duplicate cleanup detected (status 42)
candidate: output cleared, later cleanup is harmless (status 0)
```

The full five-test unit passed. Exact commands and receipts are in `TESTS.md`.

## Approach history

### Approach A — patch final `lscpu` cleanup

- Mechanism: skip or alter the final `free()` where the allocator aborts.
- Evidence: upstream traces show the same allocation was freed earlier in `ul_path_cpuparse()`.
- Result: rejected.
- Compatibility cost: could hide stale-pointer reads, leak a valid allocation, or leave other callers exposed.

### Approach B — change parser acceptance

- Mechanism: accept malformed CPU-list content such as `5,12-%`.
- Evidence: existing behavior treats malformed content as an error; the memory-safety fault is independent of parser policy.
- Result: rejected.
- Compatibility cost: expands input policy and can silently reinterpret broken topology data.

### Approach C — clear the caller-visible output after the error-path free

- Mechanism: preserve the first free, then assign `NULL` to `*set`.
- Evidence: canonical upstream commit, reporter confirmation, stable cherry-pick, current branch source, deterministic model, exact patch test.
- Result: accepted and already upstream.
- Compatibility cost: limited to correcting ownership state after an existing failure.

### Approach D — send a new util-linux contribution

- Mechanism: duplicate or re-express the canonical correction upstream.
- Evidence: master and stable/v2.40, v2.41, and v2.42 already contain free-then-NULL.
- Result: retired.
- Compatibility cost: duplicate review and divergence risk with no product benefit.

### Approach E — downstream Debian trixie backport

- Mechanism: carry canonical patch `4581ede...` in Debian stable's util-linux package.
- Evidence: trixie remains at `2.41-5`; upstream `v2.41` lacks the NULL assignment; Debian's published `2.41-5` quilt series has no cpuset, `lib/path.c`, or canonical-commit match.
- Result: selected remaining lane, held pending exact package-level execution.
- Compatibility cost: one upstream-authored source patch plus Debian packaging metadata.

## Selected correction

Retain the canonical upstream patch unchanged, including authorship and commit identity. Apply it to the exact Debian trixie `util-linux 2.41-5` source package. Add only the package metadata required by the selected Debian delivery path.

## Why the changes belong together

The source patch and a focused package regression share one invariant: a helper that frees caller-visible output on failure must clear that output before returning. Debian metadata belongs in the same downstream carrier because it declares and ships the exact backport. Any broader lscpu parser, cgroup, Incus, or topology changes belong elsewhere.

## Compatibility analysis

- **Status and stderr:** parse failure remains a failure; no success is manufactured.
- **Ordinary output:** successful parsing and ordinary `lscpu` output are untouched.
- **Cleanup:** the first free remains owned by `ul_path_cpuparse()`; later cleanup receives NULL.
- **Memory ownership:** stale caller-visible ownership is removed.
- **Platforms:** the source correction is architecture-independent C, while reporter evidence covers ppc64el and a container fixture. Package build/test coverage still needs execution on available Debian architecture(s).
- **Versions:** upstream release 2.41 is affected; 2.41.2+ contains the correction. Stable/v2.40, v2.41, and v2.42 branches contain it, while no further 2.40.x release is expected according to the maintainer.

## Negative controls and losing mutations

- The baseline model retains the output and must return 42 with “duplicate cleanup detected.”
- A one-line fixture drift causes the exact-fixture assertion to fail before patch execution.
- Patch application uses `--fuzz=0`; fuzzy application is rejected.
- The test verifies `cpuset_free(*set)` precedes `*set = NULL`.

These controls show the detector can lose and that success requires the reviewed ownership order on the exact retained fixture.

## Current upstream and historical review

- util-linux issue #3641: maintainer identifies `ul_path_cpuparse()`; reporter confirms fix.
- util-linux commit `4581ede...`: canonical one-file correction.
- util-linux commit `3cd5f1d...`: observed stable cherry-pick.
- util-linux issue #4401: later malformed-input reproducer and stable-branch release discussion.
- Linux Fieldwork issue #234: completed source archaeology and adoption map.
- Linux Fieldwork PR #239: superseded draft carrier.
- Linux Fieldwork PR #387: merged exact patch, model, fixture, and regression carrier.

Current source checks on 2026-08-01 confirm free-then-NULL in upstream master and stable/v2.40, v2.41, and v2.42.

Debian's current suite map distinguishes two states:

- trixie stable: `2.41-5`, affected upstream source line with no matching published quilt patch;
- forky/sid: newer 2.42.2 package line, fixed through upstream release adoption.

The trixie conclusion combines three public facts and remains an inference until the exact source package is unpacked and tested.

## Remaining questions

1. **Does the exact Debian `2.41-5` effective source still contain the stale error path?**  
   Discriminator: unpack `util-linux_2.41.orig.tar.xz` plus `util-linux_2.41-5.debian.tar.xz`, apply Debian quilt series, and record the final `lib/path.c` bytes/hash.

2. **Does the canonical patch apply to that effective source with zero fuzz?**  
   Discriminator: dry-run and real application with `--fuzz=0`, retaining output and final diff.

3. **Can the package-level failure be reproduced and cleared?**  
   Discriminator: run issue #4401's exact archive or a validated equivalent against baseline and rebuilt package, preferably with ASan or Valgrind where feasible.

4. **Does ordinary behavior remain compatible?**  
   Discriminator: compare representative valid `lscpu` text/JSON outputs and exit status before/after the backport.

5. **Which Debian delivery path is appropriate?**  
   Discriminator: after technical completion, owner chooses BTS patch/follow-up, Salsa merge request, or hold; external authorization remains mandatory.

## Evidence boundary

Demonstrated: exact source correction, upstream confirmation, active stable-branch inclusion, current Debian suite versions, absence of relevant strings in the published trixie quilt series, deterministic baseline/candidate distinction, exact fixture identity, zero-fuzz patching, and losing drift control.

Unexecuted: Debian source unpack, quilt result, package build, actual attachment, sanitizer run, package binary comparison, stable-update policy review, and any public submission.

## Reopen triggers

- Debian trixie publishes a package containing upstream 2.41.2+ or the canonical patch;
- exact package unpack shows an equivalent hidden correction;
- the canonical patch conflicts with Debian's effective source;
- package-level tests reveal a second owner or compatibility regression;
- issue #397 corrects unit 23 to a genuinely separate cgroup-mount defect with distinct carriers;
- explicit external-contact authorization is granted or withdrawn.
