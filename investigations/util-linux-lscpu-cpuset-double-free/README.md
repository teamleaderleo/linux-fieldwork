# util-linux `lscpu` cpuset double-free fix map

## TL;DR

The `lscpu` crash reported against util-linux 2.40 and 2.41 already has a canonical upstream fix and stable-branch backports.

The real owner is `lib/path.c:ul_path_cpuparse()`, not the final `lscpu_free_context()` call where the abort appears. On invalid CPU-list input, `ul_path_cpuparse()` freed the allocated cpuset but left the caller's pointer non-null. Later lscpu cleanup freed the stale pointer again.

Main commit `4581ede384f22983d6155768635ce43cb5304cb0` adds `*set = NULL` after the error-path free. The original ppc64el reporter confirmed the patch. The util-linux maintainer later stated that the commit was present in stable/v2.40, stable/v2.41, and stable/v2.42, while warning that another 2.40.x release was not expected.

No new product implementation is useful. The remaining work is downstream version/adoption mapping.

## Explain like I'm five

A helper allocates a CPU map, discovers that the input is broken, and throws the map away. It forgets to erase the address written on the caller's note. Later cleanup follows that stale address and tries to throw the same map away again.

The fix erases the address immediately after the first free.

## Why care

`lscpu` is used by installers, package tests, containers, support tools, and hardware inventory. Malformed or transient sysfs topology should produce a controlled error, not heap corruption. The visible abort occurs during final cleanup, which can mislead investigation toward the final free rather than the earlier ownership transfer.

## Source and authority

- Project: util-linux
- Controlled fork available: `teamleaderleo/util-linux`
- Linux Fieldwork issue: #234
- Public report: https://github.com/util-linux/util-linux/issues/4401
- Canonical earlier report: https://github.com/util-linux/util-linux/issues/3641
- Canonical main commit: https://github.com/util-linux/util-linux/commit/4581ede384f22983d6155768635ce43cb5304cb0
- Observed backport commit: https://github.com/util-linux/util-linux/commit/3cd5f1dd69495864f3046cdbcefa104786fe5a27
- External contact: unauthorized and not made

## Reported trigger

The later report retained a synthetic sysfs tree whose online CPU-list file contained malformed content:

```text
5,12-%
```

Affected releases included 2.40.4 and 2.41. A 2.42 build did not abort. The final debug output showed the process freeing CPU/type state and then aborting from a later free.

The earlier ppc64el report observed the same ownership class in cache shared maps and supplied Valgrind evidence showing an allocation from `__sched_cpualloc`, a free inside the cpuset parse path, later invalid reads, and a second free during lscpu cleanup.

## Actual source owner

Before the correction, `ul_path_cpuparse()` ended with:

```c
out:
        if (rc)
                cpuset_free(*set);
        free(buf);
        return rc;
```

When parsing failed:

1. `*set` pointed to allocated cpuset storage;
2. the helper freed it;
3. the pointer value remained visible to the caller;
4. caller-owned structures retained the stale pointer;
5. later cleanup attempted another free.

The final free is where the allocator detects corruption, but the ownership defect occurs at the first error-path free.

## Canonical correction

Main commit `4581ede384f22983d6155768635ce43cb5304cb0` changes one file and two semantic lines:

```diff
-if (rc)
+if (rc) {
        cpuset_free(*set);
+       *set = NULL;
+}
```

This preserves the error status and successful path. It makes the caller-visible ownership state match the completed free.

The earlier reporter confirmed that this patch fixed the double free. A later comment explicitly identified `4581ede...` as the fixing commit.

Backport commit `3cd5f1dd69495864f3046cdbcefa104786fe5a27` carries the same one-file diff and records that it was cherry-picked from `4581ede...`.

## Stable branch state checked 2026-07-31

The util-linux maintainer stated:

```text
The commit should now be in stable/v2.{40,41,42} branches,
but I don't expect any v2.40.x release.
```

Direct source checks confirmed the nulling correction in:

- `stable/v2.40` `lib/path.c`;
- `stable/v2.41` `lib/path.c`.

The maintainer statement is the retained authority for stable/v2.42 in this pass. A future release-adoption sweep should map exact tags and distribution packages rather than infer package status from branch content.

## Why no new patch is appropriate

The Linux Fieldwork issue originally proposed bisecting and developing a backport. That work is already complete upstream:

- canonical cause identified;
- focused mainline correction committed;
- original reproducer owner confirmed the fix;
- stable branches received the correction;
- the later report linked the earlier fix and asked only about stable release delivery.

Creating a second implementation would duplicate canonical work and risk diverging from the one-line ownership contract.

## Remaining downstream question

Branch inclusion does not guarantee a released package includes the fix.

Useful follow-up work is a version map:

1. identify the first release tags containing the correction for 2.41 and 2.42;
2. record that no later 2.40.x release is expected unless policy changes;
3. inspect maintained distribution packages still shipping an affected 2.40/2.41 source;
4. distinguish packages carrying the backport from packages relying only on branch state;
5. retire any downstream patch when the packaged upstream release contains the canonical commit.

That work belongs to LF-36 downstream patch retirement, not a new util-linux code fix.

## Compatibility and negative ramifications

The canonical patch is narrow, but review still benefits from understanding why nulling matters:

- skipping the later free without clearing ownership could hide stale-pointer reads;
- allocating a replacement map on parse failure would change error behavior;
- accepting malformed CPU lists could turn a memory-safety fix into parser-policy expansion;
- changing final lscpu cleanup would treat a symptom shared by other callers.

Nulling immediately after free is the smallest ownership correction and preserves the parser's existing failure result.

## Evidence boundary

This record maps public issue discussion, exact source diffs, reporter confirmation, and stable-branch state. It does not rerun the attachment under ASan or prove every downstream package version.

The absence of a fresh sanitizer run does not block the stop decision because canonical implementation and reporter validation already exist. It does limit claims about unrelated malformed cpuset inputs or additional ownership defects.

## Disposition

**RETIRE NEW IMPLEMENTATION; RETAIN FIX/RELEASE MAP.** Close Linux Fieldwork issue #234 as completed source archaeology. Route any package-version follow-up to LF-36 and recheck stable tags before asserting a downstream package is fixed.