# Debian BTS draft — util-linux trixie cpuset double-free backport

**DRAFT — DO NOT SEND. External contact is unauthorized. Package-level verification remains incomplete.**

## Proposed subject

`util-linux: backport upstream cpuset double-free fix to trixie`

## Proposed body

Package: util-linux  
Version: 2.41-5  
Severity: important

Debian trixie ships util-linux 2.41-5. Upstream util-linux 2.41 contains an error-path ownership defect in `lib/path.c:ul_path_cpuparse()`:

```c
out:
        if (rc)
                cpuset_free(*set);
        free(buf);
        return rc;
```

When CPU-list or mask parsing fails after allocation, the helper frees the cpuset but leaves the caller-visible pointer non-NULL. Later ordinary `lscpu` cleanup can read or free the stale pointer again.

Upstream fixed this in commit:

`4581ede384f22983d6155768635ce43cb5304cb0` (`lib/path: avoid double free() for cpusets`)

The correction is:

```diff
-if (rc)
+if (rc) {
        cpuset_free(*set);
+       *set = NULL;
+}
```

The original reporter confirmed the patch in util-linux issue #3641. A later report, util-linux issue #4401, reproduced the same ownership failure with malformed CPU-list input and records stable-branch backports. Upstream releases 2.41.2 and later include the correction.

The published Debian 2.41-5 quilt series has no `lib/path.c` cpuset patch or reference to the canonical commit. Please consider carrying the upstream patch in a trixie stable update.

Proposed patch: `patches/0001-clear-cpuset-output-after-error.patch` in the Linux Fieldwork unit packet, retaining upstream authorship.

### Verification to insert before sending

- exact unpacked Debian `2.41-5` effective `lib/path.c` hash and stale source excerpt;
- zero-fuzz patch dry-run and application output;
- baseline package/reproducer result;
- rebuilt package/reproducer result;
- valid `lscpu` output/status compatibility comparison;
- util-linux native focused test result;
- clean rebuild/rerun and artifact identities.

### References

- upstream issue #3641: `https://github.com/util-linux/util-linux/issues/3641`
- upstream fix: `https://github.com/util-linux/util-linux/commit/4581ede384f22983d6155768635ce43cb5304cb0`
- later report #4401: `https://github.com/util-linux/util-linux/issues/4401`
- Debian trixie package: `https://packages.debian.org/trixie/util-linux`
- Debian 2.41-5 patch series: `https://sources.debian.org/patches/util-linux/2.41-5/`

Regards,

`<authorized sender>`

## Send gate

Send only after:

1. package-level verification in `TESTS.md` is complete;
2. exact Debian destination and reporting conventions are rechecked;
3. repository owner grants explicit external-contact authorization;
4. sender identity and final artifact links are supplied.
