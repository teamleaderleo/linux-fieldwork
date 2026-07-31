# Hook-free hard-failure scheduling with phase-scoped fixture ownership

State: `current-main repair — fresh gate pending`

## TL;DR

Run `root-without-cap-sys-admin` without host APT hooks while preserving ordinary failures as hard failures.

The focused phase needs `create-directory` first because it creates `tar1.txt`. The broad host-hook phase also needs to run `create-directory` because its consumers execute with a different wrapper and hook set. The producer is therefore an explicit focused prerequisite, not a hook-free-only test.

## Why care

A persistent fixture records the context that created it. Reusing a hook-free archive listing in a host-hook phase produces a convincing comparison failure even when both product commands succeed.

Each execution phase must regenerate the baseline used by its own consumers.

## Candidate contract

- accept `Needs-Hook-Free-APT-Config` metadata;
- mark only `root-without-cap-sys-admin` as the hook-free-only consumer;
- fail closed when no hard consumer is selected;
- prepend exact prerequisite `create-directory` to the focused invocation;
- execute focused order `create-directory root-without-cap-sys-admin`;
- allow broad coverage to execute `create-directory` normally;
- preserve child statuses 1 and 2;
- map timeout status 124 to neutral 77;
- return 77 when the time budget is exhausted;
- apply the retained patch with zero fuzz and zero offset;
- retain the original capability drop, `/proc/self/fd`, tar, and archive assertions.

## Exact fixture relationship

Focused and broad `create-directory` executions write:

```sh
tar -C /tmp/debian-chroot --one-file-system -c . | tar -t | sort >tar1.txt
```

The capability and later broad consumers read:

```sh
diff -u tar1.txt -
```

The filename is shared; its valid identity is phase-specific.

## Executed evidence

PR #72 run 939 proved that the capability command succeeded and then lacked `tar1.txt`.

Run 974 executed the focused producer and capability consumer together; both passed. The later broad phase skipped `create-directory`, then `unshare-as-root-user` completed mmdebstrap and failed only because its host-hook archive contained three APT configuration files absent from the retained hook-free baseline.

Exact broad-only paths:

```text
./etc/apt/preferences.d/90autopkgtest
./etc/apt/sources.list.d/autopkgtest.list
./etc/apt/sources.list.d/debian.sources
```

This is phase-scoped fixture evidence, not a product failure.

## Four-file fence

- this README;
- `0001-run-hook-free-capability-case-as-hard-failure.patch`;
- `tests/test_mmdebstrap_hook_free_hard_failure.py`;
- `tests/test_mmdebstrap_hook_free_hard_failure_guards.py`.

The three executable blobs are byte-identical to PR #72 head `c0d75729432c5b7a380529eb9bdd40008c605264`.

## Evidence boundary

This focused carrier proves scheduling, fixture regeneration policy, status classification, exact patch application, and imported-source invariants. PR #72 owns real Debian sid package execution and the next independent failure.

No imported source is modified. External contact is unauthorized and none is included.
