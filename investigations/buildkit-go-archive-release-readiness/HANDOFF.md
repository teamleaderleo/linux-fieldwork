# Handoff — BuildKit / go-archive release readiness

State: `ACTIVE — direct implied-parent matrix launched`  
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
| go-archive v0.2.0 | tag `v0.2.0` |
| go-archive v0.2.1 | tag `v0.2.1` |
| go-archive v0.3.0 | tag `v0.3.0` |
| repaired go-archive main | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` |
| investigation PR head before this checkpoint | `26621980368c75b01d738ecb7f59ce06603593a4` |
| workflow installation on research base | `dc5a109dda5b742cc1a53548a352717fa74c7912` |

Use the branch ref for the latest documentation head.

## Completed

- refreshed go-archive current `main` and retained exact repair identities;
- added a standalone Go module under `probe/`;
- added an explicit-parent passing control;
- added a directory-with-implied-parent discriminator;
- defined a four-state matrix across v0.2.0, v0.2.1, v0.3.0, and repaired current `main`;
- installed the workflow on the internal research base so GitHub can execute it for pull requests;
- opened internal draft PR #416;
- retained the unsafe-test boundary for old direct absolute-symlink extraction;
- made no upstream contact.

## Current executable gate

The probe creates:

```text
etc/dnf/
etc/dnf/dnf.conf
```

without an `etc/` header and extracts it through `archive.Untar`. The explicit-parent control includes `etc/` and must pass in every row.

The matrix declares these expected outcomes:

| Candidate | Expected implied-parent result |
| --- | --- |
| v0.2.0 | pass |
| v0.2.1 | fail |
| v0.3.0 | fail |
| current main `9e6d2c7...` | pass |

Each row records the exact checkout SHA, Go version, kernel, and clean go-archive source state.

## Harness correction

The first PR head did not schedule the new workflow because GitHub evaluates `pull_request` workflows from the base branch. The identical workflow was installed on the internal research base, and this checkpoint advances the PR head so the merge-ref can execute it.

This was a harness ownership issue, not a product result.

## Safety boundary

The direct matrix intentionally covers only implied-parent behavior. It does not run old direct `Untar` versions through absolute symlinks such as `var/run -> /run`, because older unbounded implementations could follow the host-root target. Absolute-symlink and hard-link compatibility must run in a disposable container, chroot, or BuildKit integration sandbox.

## First incomplete step

1. classify the exact four-row workflow result;
2. retain logs and exact candidate SHAs;
3. rerun the matrix once from a clean merge ref;
4. update `README.md` and `TESTS.md` with the direct result;
5. move to contained BuildKit integration cases for implied parents and absolute symlinks;
6. add metadata, hard-link identity, confinement, cleanup, and performance gates before any dependency-bump recommendation.

## Stop conditions

- equivalent active BuildKit dependency-bump work appears;
- the defining integration sandbox is unavailable;
- the first red result belongs to stale source, module selection, toolchain, or fixture setup;
- containment negative controls weaken;
- cleanup cannot prove no retained process, mount, socket, trace, temporary tree, or module mutation.

## Authority

Internal fork synchronization, branches, tests, benchmarks, and evidence records are allowed. No public BuildKit or go-archive issue, pull request, comment, review, or email is authorized.
