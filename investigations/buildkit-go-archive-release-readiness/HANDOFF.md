# Handoff — BuildKit / go-archive release readiness

State: `ACTIVE — direct implied-parent matrix green; BuildKit integration pending`  
Linux Fieldwork branch: `investigation/buildkit-go-archive-matrix`  
Internal draft PR: #416  
External contact authorized: `false`  
External contact made: `none`

## Exact current identities

| Item | Identity |
| --- | --- |
| BuildKit rollback merge | `275d6864ff0ce91a06225af5f5b012887bd257cf` |
| BuildKit rollback test head | `22ea4efb43c3c91651dab7f44d1599c4c42b9412` |
| user's observed BuildKit fork head | `df0761886a20e368d75e0aa6bb3f20874f58b692` |
| go-archive v0.2.0 | `263611f5f0914b2a153d86dae2042d13be6a88c4` |
| go-archive v0.2.1 | `0bfb09625293006825b7a57ffca9b9552eb9d872` |
| go-archive v0.3.0 | `1c23372e409716c3691a540871806083644f348a` |
| repaired go-archive main | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` |
| green direct-matrix technical head | `243b27ae7e9862dda5f6f6c64481eeef8e4c424b` |
| exact direct-matrix run | `30793638884` |
| retained matrix receipt | `artifacts/direct-implied-parent-matrix-2026-08-03.md` |

Use the branch ref for the latest documentation head.

## Completed

- added a standalone direct-library probe with an explicit-parent passing control and a directory-with-implied-parent discriminator;
- mapped archive UID/GID 0 to the current runner UID/GID so every dependency state executes under equal unprivileged ownership conditions;
- ran v0.2.0, v0.2.1, v0.3.0, and repaired current main on Ubuntu 24.04 / kernel `6.17.0-1020-azure`;
- proved the intended compatibility split exactly;
- proved tracked checkout, candidate checkout, and temporary probe cleanup in every row;
- retained the prior v0.2.0 `lchown` red as a harness-owned result, not product evidence;
- mapped the BuildKit integration registration under `frontend/dockerfile` and `TestIntegration`;
- made no upstream contact.

## Exact direct result

| Candidate | Implied-parent result | Explicit-parent control |
| --- | --- | --- |
| v0.2.0 | pass | pass |
| v0.2.1 | expected fail | pass |
| v0.3.0 | expected fail | pass |
| current main `9e6d2c7...` | pass | pass |

The failing controls report the expected missing-parent errors:

- v0.2.1: `mkdir .../etc/dnf: no such file or directory`;
- v0.3.0: `mkdirat etc/dnf: no such file or directory`.

The two passing rows extracted `implied-parent-ok\n`.

## Safety boundary

The direct matrix intentionally covers only implied-parent behavior. It does not run old direct `Untar` versions through absolute symlinks such as `var/run -> /run`, because older unbounded implementations could follow the host-root target. Absolute-symlink and hard-link compatibility must run in a disposable container, chroot, or BuildKit integration sandbox.

## First incomplete step

1. refresh the controlled BuildKit fork from exact rollback/test head;
2. run `testDockerfileAddArchiveWithImpliedParentDir` and `testDockerfileAddArchiveThroughAbsoluteSymlink` through a real BuildKit sandbox;
3. compare v0.2.0, v0.2.1, v0.3.0, and repaired main under the same backend;
4. retain hard-link inode identity, relative-escape rejection, whiteout/deferred-metadata, cleanup/rerun, and performance results;
5. refresh overlap before recommending or preparing a dependency bump.

## Stop conditions

- equivalent active BuildKit dependency-bump work appears;
- the defining integration sandbox is unavailable;
- the first red result belongs to stale source, module selection, toolchain, or fixture setup;
- containment negative controls weaken;
- cleanup cannot prove no retained process, mount, socket, trace, temporary tree, or module mutation.

## Authority

Internal fork synchronization, branches, tests, benchmarks, and evidence records are allowed. No public BuildKit or go-archive issue, pull request, comment, review, or email is authorized.
