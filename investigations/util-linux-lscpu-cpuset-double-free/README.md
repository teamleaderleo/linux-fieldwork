# util-linux lscpu cpuset double-free ownership

## TL;DR

The crash is caused by a stale pointer, not by the final `free()` itself.

A shared util-linux parser allocates a CPU set and publishes its address to the caller. When the sysfs text is malformed, the parser frees that CPU set but leaves the caller's pointer unchanged. `lscpu` later performs ordinary context cleanup and frees the same address again.

The canonical upstream correction is one ownership line:

```c
cpuset_free(*set);
*set = NULL;
```

Commit `4581ede384f22983d6155768635ce43cb5304cb0` landed on 2025-07-02, was confirmed against the original ppc64el report, appears in util-linux 2.41.2, and is now present on the upstream stable 2.40, 2.41, and 2.42 branches.

Debian 13/trixie still carries source version `2.41-5`, which predates that correction. Its Debian patch series does not contain the cpuset ownership fix. Ubuntu carried the canonical commit in `2.41-4ubuntu3`.

## Explain it like I am five

Imagine a helper writes a locker number on your card, discovers the locker contents are broken, and empties the locker. The helper forgets to erase the number from your card.

Later, the cleanup worker reads your card and tries to empty the same locker again. That second cleanup is the crash.

The fix erases the locker number after the first cleanup. In C, an erased pointer is `NULL`, and the later cleanup already treats `NULL` as “nothing to free.”

## Why should anyone care?

`lscpu` is used by installers, package builds, hardware inventory, containers, CI, support scripts, and monitoring tools. A malformed or inconsistent synthetic sysfs snapshot should produce a controlled parse error. Heap corruption during cleanup can abort the process and obscures the original bad input.

The affected helper lives in shared `lib/path.c`, so the ownership rule applies beyond one NUMA call site. Removing a final `free()` in `lscpu` would only hide one symptom and could leak memory or leave another caller exposed.

## Exact reports

### Original confirmed report

util-linux issue 3641 reported a repeatable `lscpu` double free during an Ubuntu ppc64el package build. The maintainer traced the owner to `ul_path_cpuparse()`: it freed a CPU set after parse failure without clearing the output pointer. The reporter applied the current-tree patch to 2.41 and confirmed that it fixed the crash.

- report: https://github.com/util-linux/util-linux/issues/3641
- canonical commit: https://github.com/util-linux/util-linux/commit/4581ede384f22983d6155768635ce43cb5304cb0

### Retained synthetic NUMA report

util-linux issue 4401 supplied a generated `lscpu -s` input whose malformed CPU text crashes released 2.40.4 and 2.41 while 2.42 survives. Its debug trace reaches `lscpu_free_context()` while freeing `nodemaps`. The issue discussion identifies issue 3641 as the existing correction.

- report: https://github.com/util-linux/util-linux/issues/4401
- reported malformed input excerpt: `sys/devices/system/cpu/online` contains `5,12-%`
- attached archive: `test.tar.gz`

The attachment URL was visible but unavailable through this session's repository and public-download paths. This record therefore separates exact source ownership and upstream confirmation from execution of that exact archive.

## Version boundary

| Source state | Result or code state |
|---|---|
| util-linux 2.40.4, tag `dbcc687f6ab1568982cdf3fe391c0beb818b7e28` | released before the correction; retained report says the synthetic input crashes |
| util-linux 2.41, tag `caa26876bc75041833c9644491cc2670d623f750` | parser frees failed CPU set without clearing the caller's pointer; retained reports reproduce a double free |
| canonical commit `4581ede384f22983d6155768635ce43cb5304cb0` | adds `*set = NULL` after error-path free |
| util-linux 2.41.2 and current stable/v2.41 | correction included |
| util-linux 2.42, tag `04d22901dd3d91d25e985596d588b9cec1ee267d` | corrected parser; retained synthetic input does not reproduce |
| current stable/v2.40 | correction present; maintainer expects no further 2.40.x release |

## Code map

### Entrypoint for the retained NUMA path

`sys-utils/lscpu-cputype.c` contains `lscpu_read_numas()`.

It:

1. counts NUMA node directories;
2. allocates `cxt->nodemaps`, an array of CPU-set pointers;
3. calls `ul_path_readf_cpuset()` for every node's `cpumap` file;
4. leaves final context cleanup to `lscpu_free_context()`.

The NUMA reader is materially the same in released 2.41 and 2.42. That points away from the final cleanup loop and toward the shared parser used to fill each array slot.

### Shared parser and ownership handoff

`lib/path.c` contains this call chain:

```text
ul_path_readf_cpuset()
        |
        v
ul_path_cpuparse(..., cpu_set_t **set, ...)
```

The `cpu_set_t **set` parameter means the function can replace the caller's pointer.

On entry:

```c
*set = NULL;
```

After reading the file:

```c
*set = cpuset_alloc(...);
```

At this point the caller's array slot owns the new allocation.

### Failing branch in 2.40/2.41

When `cpumask_parse()` rejects malformed text, execution reaches:

```c
out:
    if (rc)
        cpuset_free(*set);
```

The allocation is released, while `*set` still contains its old address.

The function returns an error. Its caller ignores that return value in the NUMA loop, and the stale pointer remains in `cxt->nodemaps[i]`.

### Later cleanup

`lscpu_free_context()` eventually runs:

```c
for (i = 0; i < cxt->nnodes; i++)
    free(cxt->nodemaps[i]);
```

That cleanup is ordinary when every slot is either a live allocation or `NULL`. The parser violated that contract by returning a freed non-NULL address.

### Canonical correction

The upstream change turns the failure branch into:

```c
out:
    if (rc) {
        cpuset_free(*set);
        *set = NULL;
    }
```

Now the parser communicates both facts:

- parsing failed;
- the caller owns no allocation.

The later cleanup receives `NULL`, and freeing `NULL` is harmless.

## Why this is the right repair boundary

Several tempting fixes target the symptom:

- skip freeing NUMA maps during `lscpu` shutdown;
- ignore malformed cpumap input;
- add a one-off condition in `lscpu_free_context()`;
- catch the abort around `lscpu` execution.

Those choices leave the shared parser's ownership contract broken. The canonical correction repairs the function that creates the dangling pointer and preserves normal cleanup for every caller.

## Executable ownership model

The retained archive could not be executed in this session, so the repository includes a deterministic C model of the ownership sequence:

```text
parser publishes allocation
        |
parse error frees allocation
        |
baseline keeps stale output address
        |
outer cleanup sees same address again
```

`ownership_model.c` uses a tracker instead of issuing an actual second `free()`. That keeps CI deterministic and avoids deliberate undefined behavior.

`run_model.py` compiles two variants:

- baseline: duplicate cleanup is detected, status 42;
- candidate: `CLEAR_OUTPUT_AFTER_ERROR` clears the pointer, later cleanup succeeds, status 0.

Run:

```sh
python3 investigations/util-linux-lscpu-cpuset-double-free/run_model.py
python3 -m unittest tests.test_util_linux_lscpu_cpuset_double_free -v
```

The local focused result was:

```text
baseline: duplicate cleanup detected (status 42)
candidate: output cleared, later cleanup is harmless (status 0)
```

## Retained patch

`0001-clear-cpuset-output-after-error.patch` preserves the canonical upstream commit's source change and authorship. This repository does not claim authorship of that correction.

The patch is intentionally tiny because the source evidence identifies a clean ownership repair. A downstream backport should retain that exact change instead of modifying `lscpu` cleanup.

## Downstream map checked 2026-07-31

### Upstream util-linux

- canonical fix committed on 2025-07-02;
- reporter confirmed the fix on affected 2.41;
- included in 2.41.2;
- present in stable/v2.40, stable/v2.41, and stable/v2.42;
- maintainer stated that another 2.40.x release is unlikely.

### Ubuntu

Ubuntu `2.41-4ubuntu3` records:

```text
lib/path: avoid double free() for cpusets (LP: #2115636)
```

Ubuntu therefore supplies a practical downstream precedent for carrying the one-line correction before rebasing to a newer upstream release.

### Debian

Debian 13/trixie carries util-linux `2.41-5`, accepted in May 2025 before the July correction. Debian Sources still associates `2.41-5` with trixie, and its patch listing does not contain this cpuset ownership fix.

Current Debian development suites have moved through 2.41.2, 2.41.3, and 2.42, so the live gap is the frozen trixie source rather than current unstable.

## Evidence boundary

This record establishes:

- the precise ownership defect in released 2.40.4 and 2.41 source;
- the canonical upstream correction and confirmation;
- its presence in current upstream stable branches and 2.41.2+;
- an executable local model of the stale-output-pointer contract;
- a likely Debian 13/trixie backport gap.

This record does not yet establish:

- execution of issue 4401's exact attached archive;
- a local Debian `2.41-5` package build with the patch;
- normal, parse, JSON, topology, and leak checks against Debian binaries;
- whether Debian stable maintainers already have an unpublished or pending update;
- authorization to contact Debian or util-linux.

## Next executable decision

Before any Debian proposal:

1. obtain and hash the exact issue 4401 archive;
2. reproduce against Debian trixie `2.41-5` under ASan or Valgrind;
3. apply the canonical patch to Debian source;
4. rerun the exact archive plus ordinary host, summary, parse, JSON, and topology controls;
5. run the relevant util-linux test suite;
6. clean the build tree and repeat the patched fixture run;
7. check Debian bug and proposed-update queues again;
8. seek a deliberate external-contact decision.

## Disposition

**HOLD** for exact fixture execution and Debian package-level verification.

The source owner, canonical correction, upstream stable state, Ubuntu precedent, and likely Debian stable gap are mapped. The remaining work is a bounded downstream confirmation, not a new product fix.

No external issue, email, patch submission, merge request, comment, or review was created.