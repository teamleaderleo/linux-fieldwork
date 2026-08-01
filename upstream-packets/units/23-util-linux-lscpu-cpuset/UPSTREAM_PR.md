# Debian Salsa merge-request draft — backport util-linux cpuset ownership fix

**DRAFT — DO NOT OPEN. External contact is unauthorized. Exact package verification remains incomplete.**

## Proposed title

`Backport upstream lscpu cpuset double-free fix to trixie`

## Proposed summary

This change carries upstream util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` in the trixie package line.

On CPU-list or mask parse failure, `lib/path.c:ul_path_cpuparse()` frees the allocated cpuset. util-linux 2.41 leaves the freed address in the caller-visible output. Later ordinary `lscpu` cleanup can reach the stale pointer again.

The upstream correction clears the output immediately after the first free:

```c
if (rc) {
        cpuset_free(*set);
        *set = NULL;
}
```

The parse result and successful path remain unchanged. The original upstream reporter confirmed the correction, and current util-linux stable branches contain it.

## Proposed commits

1. `lib/path: avoid double free() for cpusets`
   - import canonical upstream patch with original authorship;
   - add it to the Debian patch series.
2. `debian/changelog: document trixie backport`
   - package version and target suite to be selected by the Debian maintainer path.

## Verification to insert before opening

```text
Exact Debian base:
Effective lib/path.c hash:
Patch dry-run:
Patch application:
Baseline reproducer:
Candidate reproducer:
Valid text output comparison:
Valid JSON output comparison:
Native focused tests:
Package build:
Autopkgtest:
Cleanup and immediate rerun:
```

Fresh Linux Fieldwork retained evidence already passes:

```text
5 focused tests passed
baseline model: duplicate cleanup detected (status 42)
candidate model: output cleared, later cleanup harmless (status 0)
exact fixture identity: pass
zero-fuzz patch application: pass
fixture drift control: pass
```

## Compatibility

- successful CPU-list and mask parsing is unchanged;
- malformed input remains an error;
- the first error-path free remains in the same owner;
- caller-visible ownership now reflects the completed free;
- later NULL-safe cleanup remains ordinary behavior.

## Boundaries

This merge request would carry the canonical source fix only. It would not alter parser policy, final `lscpu` cleanup, cgroup mount selection, Incus behavior, or unrelated topology handling.

## Open gate

Open only after exact package-level execution is complete, the destination branch/version is selected, and explicit external-contact authorization is recorded.
