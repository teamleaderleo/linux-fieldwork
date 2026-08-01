# Upstream pull-request draft

Status: internal draft only; external contact is unauthorized.

## Title

`file-mirror-automount: contain setup and cleanup targets`

## Summary

The file-mirror hook now resolves source and destination identities before acting and requires every generated target to remain a strict child of the generated root.

Setup now:

- canonicalizes the generated root and refuses `/`;
- rejects `file:` repository paths containing a parent component;
- canonicalizes the existing host source;
- preserves the configured URI path as the in-root destination for terminal source symlinks;
- resolves existing destination symlinks before the containment decision;
- records canonical root-relative NUL-delimited cleanup entries only after successful actions.

Cleanup now:

- treats every marker entry as untrusted input;
- validates the complete marker before the first unmount or recursive removal;
- revalidates each target immediately before acting;
- retains the marker after validation or action failure for diagnosis and rerun.

## Problem

The previous scripts joined the generated-root argument with repository or marker path text. Parent traversal, destination-parent symlinks, a root argument resolving to `/`, or altered marker contents could select a host path outside the generated root. Sequential cleanup could also perform partial actions before reaching a later invalid marker entry.

A source symlink adds a compatibility constraint: the host operation should use the canonical source, while APT inside the generated root still needs the configured URI path. The candidate keeps these identities separate.

## Tests

The disposable regression matrix covers:

- baseline repository traversal and candidate rejection before action;
- ordinary repository and local-package behavior;
- destination-parent symlink escape;
- literal and symlinked filesystem-root refusal;
- terminal source-symlink reachability, cleanup, and rerun;
- harmless dot normalization;
- leading and embedded parent-component rejection;
- mixed valid/invalid marker preflight with zero destructive actions;
- marker retention and corrected immediate rerun;
- exact patch application and POSIX shell syntax.

The tests use temporary directories and fake `mount`, `umount`, hook-helper, and destructive `rm -r` commands. They create no real mounts and require no network access.

## Compatibility

Ordinary repository and package paths keep their expected in-root locations. Terminal source symlinks remain supported. Harmless dot components and repeated separators normalize. Configured paths containing any `..` component are refused because lexical normalization can create a destination that the original URI cannot traverse to.

The cleanup marker format becomes canonical root-relative NUL entries. Historical leading-slash entries fail closed during an active cleanup.

The scripts use GNU `realpath` modes `-e`, `-m`, and `-s`, plus GNU `xargs`, consistent with the existing Linux/GNU hook environment.

## Remaining boundary

The implementation continues to use pathname check-then-act operations. A sufficiently capable concurrent actor may replace a path or marker component after validation and before the corresponding mount, copy, unmount, or removal. Descriptor-relative operations or a private mount namespace would be a larger follow-up.

## Patch organization

This pull request contains one commit because setup writes the cleanup authority and cleanup consumes it. The complete lifecycle invariant is easier to review and test as one source unit.
