# PR #395 live-head complete-diff review

Reviewed: `2026-08-01`  
Live PR head: `74c996394819c3a717d55193d84336c2e06b3b7c`  
Generated merge used by the latest dedicated run: `a7fa7fe838e499ee52912c7be276cc89cfad4dec`  
External contact: `false; none occurred`

## Review fence

All nine changed paths in the live PR diff were read:

1. `.github/workflows/mmdebstrap-chrootless-directory-mtime.yml`
2. `investigations/mmdebstrap-chrootless-directory-mtime/0001-normalize-root-chrootless-directory-mtimes.patch`
3. `investigations/mmdebstrap-chrootless-directory-mtime/PRODUCT-CANDIDATE.md`
4. `investigations/mmdebstrap-chrootless-directory-mtime/prepare_product_normalizer.py`
5. `investigations/mmdebstrap-chrootless-directory-mtime/real_metadata_probe.sh`
6. `tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py`
7. `tests/test_mmdebstrap_chrootless_directory_mtime_patch_context.py`
8. `tests/test_mmdebstrap_chrootless_directory_mtime_product_probe.py`
9. `tests/test_mmdebstrap_chrootless_directory_mtime_real_probe.py`

No inline review threads exist on PR #395.

## Finding 1 — directory atime is overwritten

The product patch contains:

```perl
1 == utime($mtime, $mtime, $File::Find::name)
```

Perl `utime(ATIME, MTIME, PATH...)` assigns both timestamps. The live candidate therefore sets directory access time and modification time to the epoch.

This conflicts with unit 17's intended boundary, which preserves access time while converging directory mtime. It also regresses the earlier PR #384 repair that used the observed directory atime as the first `utime` argument.

### Why the current tests miss it

`tests/test_mmdebstrap_chrootless_directory_mtime_candidate.py`:

- positively requires the exact `utime($mtime, $mtime, ...)` source string;
- asserts directory mtime convergence;
- checks regular-file, symlink, hard-link, outside-target, and rerun behavior;
- contains no before/after directory-atime assertion.

The real metadata probe checks ACL, file capability, mount exclusion, ordinary directory mtime, cleanup, and rerun. It also lacks a directory-atime reversing control.

### Disposition

PR #395 cannot represent the unit's stated product behavior at this head. Any retained pathname candidate needs both:

1. a directory-atime reversing control that fails on the current helper; and
2. a helper that captures and restores the observed directory atime while assigning only mtime.

This repair would still leave the pathname replacement/authority blocker below.

## Finding 2 — pathname authority remains unsafe

The product helper performs a path-based sequence:

1. `lstat` the current path;
2. classify it as a real same-device directory;
3. later call path-based `utime` on the same string.

A concurrent replacement between the check and mutation can change the target identity. The live diff does not retain a descriptor for mutation and does not close the issue #392 authority question.

PR #389 remains the mechanically stronger identity mechanism. PR #394 proves that descriptor identity still requires an explicit operation-ownership policy after an inode leaves the temporary root.

## Latest exact execution

### Linux Fieldwork CI

- run: `30659899178` / 1099
- head: `74c996394819c3a717d55193d84336c2e06b3b7c`
- conclusion: success

### Dedicated boundary workflow

- run: `30659899105` / 25
- job: `91253360438` (`real-metadata-boundaries`)
- generated merge: `a7fa7fe838e499ee52912c7be276cc89cfad4dec`
- conclusion: failure

Step results:

- exact patch context, synthetic matrix, and product candidate: success;
- current Debian sid formatting: failure;
- exact product helper on real metadata matrix twice: skipped;
- receipt upload: success with no files found.

The sid container applied the patch exactly and `perl -c` passed. The step then ran whole-file `perltidy` and failed:

```text
/tmp/.../mmdebstrap /tmp/mmdebstrap.tdy differ: char 1676, line 42
```

This is a formatting-gate ownership failure. The real product-helper metadata matrix never executed on the live head, and no artifact was retained.

## Review conclusion

PR #395 is useful construction and test-harness history. At live head `74c996...` it has three independent promotion blockers:

1. directory atime is overwritten;
2. pathname check-to-mutation identity and operation authority remain unresolved;
3. the dedicated exact-head run stopped at whole-source formatting before the real product matrix.

The unit remains `HOLD`. The next authority discriminator remains the archive-boundary process probe in repeated disposable root and chrootless runs. Product promotion waits for that result and a candidate that preserves directory atime.
