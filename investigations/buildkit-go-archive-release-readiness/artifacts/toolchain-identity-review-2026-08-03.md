# go-archive matrix toolchain identity review — 2026-08-03

State: `WORKFLOW REPAIR — FRESH FOUR-ROW MATRIX PENDING`  
Parent carrier: PR #416  
External contact: none

## Compatibility result retained

Exact-head run `30795042514` and Linux Fieldwork CI `30795042496` completed successfully on carrier head `130b05b919b7b5a52de86bb8cd9d5e20d1de77ed`.

The four dependency results remain:

| Candidate | Exact commit | Implied parent | Explicit parent |
| --- | --- | --- | --- |
| v0.2.0 | `263611f5f0914b2a153d86dae2042d13be6a88c4` | pass | pass |
| v0.2.1 | `0bfb09625293006825b7a57ffca9b9552eb9d872` | expected fail | pass |
| v0.3.0 | `1c23372e409716c3691a540871806083644f348a` | expected fail | pass |
| repaired main | `9e6d2c7c969f4871fe6ded98ae0e28963fde311f` | pass | pass |

Every row proved clean tracked checkout, clean candidate checkout, and removal of its disposable `goarchive-probe.*` directory.

## Review finding

The matrix declared Go `1.23.x` for v0.2.1. Setup installed Go 1.23.12, but that exact dependency commit declares:

```text
go 1.25
```

With `GOTOOLCHAIN=auto`, the retained log shows:

```text
go: module .../go-archive requires go >= 1.25; switching to go1.25.12
go: downloading go1.25.12 (linux/amd64)
...
go: downloading go1.25.0 (linux/amd64)
```

The behavior result is still valid, because the intended source and probe executed. The row's advertised toolchain identity is not valid: execution crossed two implicit toolchain selections that were absent from the matrix declaration.

The workflow also used the moving `ubuntu-latest` runner label and default checkout credential persistence before proposed source and probe code ran.

## Exact source requirements

- v0.2.0 declares `go 1.23.0`;
- v0.2.1 declares `go 1.25`;
- v0.3.0 declares `go 1.25`;
- repaired main `9e6d2c7...` declares `go 1.25`.

## Bounded repair

The stacked carrier:

- pins Ubuntu 24.04;
- selects Go 1.23.12 for v0.2.0;
- selects Go 1.25.12 for v0.2.1, v0.3.0, and repaired main;
- sets `GOTOOLCHAIN=local` for every step;
- validates exact effective `GOVERSION` before and after `go mod tidy`;
- validates each candidate's `go` directive;
- disables credential persistence in both checkouts;
- keeps the two-pass/two-expected-fail behavior matrix unchanged;
- retains the existing cleanup assertions.

A focused workflow-contract test encodes those requirements so a moving runner, hidden toolchain switch, stale version declaration, or credential regression fails before interpreting archive behavior.

## Evidence boundary

This repair changes execution identity and workflow trust boundaries only. It does not change the archive fixture, candidate commits, expected compatibility split, BuildKit integration boundary, or external-contact authority.

The prior successful matrix remains evidence for direct implied-parent behavior. A fresh matrix is required before claiming exact-toolchain reproducibility.

## Next step

Run all four rows on the repaired head. On green, record the exact runner image, effective Go version, candidate `go` directive, source commit, behavior result, and cleanup receipt. On red, classify the first failing identity or behavior check before changing expectations.
