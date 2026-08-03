# Direct go-archive implied-parent matrix — 2026-08-03

State: `GREEN — exact four-version direct library gate`  
Linux Fieldwork head: `243b27ae7e9862dda5f6f6c64481eeef8e4c424b`  
Workflow run: `30793638884`  
Merge checkout: `ee01e1e11c7b6531af8c25545c115099accbf533`  
External contact: none

## Question

When a tar archive contains `etc/dnf/` and `etc/dnf/dnf.conf` without a separate `etc/` header, which exact go-archive dependency states create the implied parent and extract the file successfully?

Every row also ran an explicit-parent control containing an `etc/` header.

## Environment

- GitHub hosted Ubuntu 24.04 runner image `20260720.247.2`
- kernel `6.17.0-1020-azure`
- `linux/amd64`
- Go 1.23.12 for v0.2.0 and v0.2.1 setup; Go 1.25.12 for v0.3.0 and current main
- archive UID/GID 0 mapped to the current runner UID/GID so all versions execute under equal unprivileged ownership conditions
- each probe module lived below a fresh `RUNNER_TEMP/goarchive-probe.*` directory

## Exact results

| Candidate | Exact commit | Declared implied-parent result | Observed result | Explicit-parent control |
| --- | --- | --- | --- | --- |
| v0.2.0 | `263611f5f0914b2a153d86dae2042d13be6a88c4` | pass | pass; extracted `implied-parent-ok\n` | pass |
| v0.2.1 | `0bfb09625293006825b7a57ffca9b9552eb9d872` | fail | expected failure: `mkdir .../etc/dnf: no such file or directory` | pass |
| v0.3.0 | `1c23372e409716c3691a540871806083644f348a` | fail | expected failure: `mkdirat etc/dnf: no such file or directory` | pass |
| repaired main | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` | pass | pass; extracted `implied-parent-ok\n` | pass |

All four jobs completed successfully because the negative-control rows explicitly required extraction to fail.

## Cleanup proof

Every row verified:

- the Linux Fieldwork tracked checkout was unchanged;
- the go-archive candidate checkout was unchanged;
- no `goarchive-probe.*` temporary directory remained;
- the test's `t.TempDir()` extraction roots were removed by the Go test harness.

## Harness correction

Earlier run `30755181400` was not a valid four-row product result. Its v0.2.0 row reached the historical implied-parent path but failed while trying to `lchown` the synthesized directory to UID/GID 0 on an unprivileged runner.

Head `243b27ae...` repaired the harness by supplying a `user.IdentityMapping` that maps archive root to the current runner UID/GID. This preserved equal privilege conditions and avoided using `sudo` for only one dependency state.

## Interpretation

The direct library discriminator now proves the historical compatibility window:

- v0.2.0 is the known-good baseline;
- v0.2.1 introduced the implied-directory regression;
- v0.3.0 still contains it;
- current main at `9e6d2c7...` repairs it.

This is not yet a BuildKit dependency-bump recommendation. The remaining release gate includes the exact BuildKit integration tests, extraction through absolute symlinks, hard-link inode identity, relative-escape rejection, whiteout/deferred-metadata paths, cleanup/rerun parity, and performance measurement.
