# Schedule `root-without-cap-sys-admin` outside host-APT hooks

## In simple words

The `root-without-cap-sys-admin` coverage case deliberately removes `CAP_SYS_ADMIN` before running `mmdebstrap --mode=root`. The Debian package test currently injects the `file-mirror-automount` hook into every case in its host-APT transition phase. That hook unconditionally bind-mounts local file repositories for root mode, so it fails before the case can test mmdebstrap's capability fallback.

The candidate marks this case as incompatible with host APT configuration. The existing package-test second phase already reruns every such case with `CMD=mmdebstrap` and without `sourcesfilter` or `file-mirror-automount`.

## Coordination

- owning issue: #153
- Debian bug investigation: #53
- execution and Deb822 reduction: PR #72
- exact confirming run: `30546575662`
- exact run head: `4a9ac8ec7394a5103495b00547984ef4df63caff`

## Confirmed failure

Current sid passed five cases, including:

- `(30/284) create-directory`;
- `(31/284) unshare-as-root-user`.

The first failure was:

```text
(41/284) root-without-cap-sys-admin
```

The generated command deliberately used:

```sh
capsh --drop=cap_sys_admin
```

`mmdebstrap` correctly reported that mount capability was unavailable and continued toward its non-mount path. The globally injected setup hook then attempted:

```sh
mount -o ro,bind /tmp/autopkgtest.../binaries ...
```

and failed with permission denied. The intended `/proc/self/fd` assertion was never reached.

## Candidate

Add to `coverage.txt`:

```text
Test: root-without-cap-sys-admin
Needs-Root: true
Needs-APT-Config: true
```

In this test framework, `Needs-APT-Config: true` means the case is skipped while `USE_HOST_APT_CONFIG=yes`. The package entrypoint later collects those case names and runs them against a forced host-architecture mirror with:

```text
CMD=mmdebstrap
```

That second command contains neither the host `sourcesfilter` setup hook nor `file-mirror-automount`.

## Why this boundary is preferable

- The shared hook remains unchanged for cases that need autopkgtest's local file repository.
- The capability case still runs; it is not permanently skipped.
- The case retains the real `capsh` drop, `/proc/self/fd` assertion, tar creation, and archive comparison.
- No capability probing or mount fallback is added to a general-purpose hook.
- No copied repository needs a second cleanup protocol.

## Executable regression

`tests/test_mmdebstrap_root_without_cap_sys_admin_scheduling.py` requires:

- the imported baseline to lack `Needs-APT-Config` for this case;
- the candidate patch to apply to the exact imported `coverage.txt`;
- the candidate to skip only when host APT configuration is active;
- the existing second phase to select `Needs-APT-Config` cases;
- the second-phase command to omit both injected hooks;
- the original capability drop and assertions to remain unchanged.

The baseline scheduling result is the negative control.

## Evidence boundary

This repairs package-test observability for case 41. It does not establish that the historical Debian run `72574145` failed at this case, and it does not change `mmdebstrap` product behavior.

## Cleanup

The regression copies one text file into a temporary directory, applies one patch, and removes the directory through test cleanup. It starts no process beyond the bounded `patch` subprocess and creates no mount, namespace, package, listener, or root filesystem.

## Disposition

**Fix candidate.** Validate in repository CI, then integrate into the current reproduction branch and rerun from the first behavioral blocker.

## Authority

No Debian or external upstream issue, email, merge request, patch submission, comment, or review is authorized or included.
