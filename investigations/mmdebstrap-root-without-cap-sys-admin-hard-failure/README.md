# Hook-free hard-failure scheduling with fixture completeness

State: `current-main focused carrier — fresh gate pending`

## TL;DR

Run the mmdebstrap capability case without host APT hooks while preserving ordinary failures as hard failures. The focused phase must include `create-directory` before `root-without-cap-sys-admin`, because the latter compares its archive listing against `tar1.txt` produced by the former.

## Why care

The capability case deliberately removes `CAP_SYS_ADMIN`. Host setup that needs that capability prevents the product question from running. Moving one case into a focused phase solved that conflict but exposed an ordered-suite dependency when run 939 selected the consumer alone.

A focused selector is complete only when it carries the exact prerequisite it removes from normal suite order.

## Candidate contract

- accept `Needs-Hook-Free-APT-Config` metadata;
- mark both `create-directory` and `root-without-cap-sys-admin`;
- preserve their original producer-before-consumer order;
- skip that class while host APT hooks are active;
- execute it later with `CMD=mmdebstrap` and without `sourcesfilter` or `file-mirror-automount`;
- preserve child statuses 1 and 2;
- map GNU timeout status 124 to neutral 77;
- return 77 when the time budget is exhausted;
- fail 1 when no test is selected;
- preserve selector-command failures;
- apply the retained patch with zero fuzz and zero offset;
- retain the original capability drop, `/proc/self/fd`, tar, and archive assertions.

## Exact fixture relationship

`tests/create-directory` writes:

```sh
tar -C /tmp/debian-chroot --one-file-system -c . | tar -t | sort >tar1.txt
```

`tests/root-without-cap-sys-admin` later reads:

```sh
tar -tf /tmp/debian-chroot.tar | sort | diff -u tar1.txt -
```

The consumer does not read `pkglist.txt`; that file is outside this exact prerequisite.

## Executed evidence

PR #72 run `30633385029` / 939 cleared carrier preflight and reached the real Debian sid package case. `/usr/bin/mmdebstrap` completed after dropping `CAP_SYS_ADMIN`; the phase then failed because `tar1.txt` was absent. This is fixture-order evidence, not an mmdebstrap product failure.

Run `30636315846` / 968 stopped before package execution because the first producer hunk used stale trailing context. That was a carrier-preflight failure with no product claim. The hunk now matches `Test: unshare-as-root-user` exactly.

The live integration carrier later passed its current repository gate on head `fe84899d7c4de599038c41ad13810b82f832baf6`, validating four patch files, nine hunks, and the complete focused controls before entering the real sid package matrix.

## Four-file fence

- this README;
- `0001-run-hook-free-capability-case-as-hard-failure.patch`;
- `tests/test_mmdebstrap_hook_free_hard_failure.py`;
- `tests/test_mmdebstrap_hook_free_hard_failure_guards.py`.

The three executable blobs are byte-identical to PR #72 head `fe84899d7c4de599038c41ad13810b82f832baf6`.

## Evidence boundary

This focused carrier proves scheduling, fixture completeness, status classification, exact patch application, and imported-source invariants. PR #72 remains the disposable sid integration carrier and owns real package behavior.

No imported source is modified on this branch. External contact is unauthorized and none is included.
