# Handoff — systemd bind-path whitespace overlap

Handoff date: 2026-08-02  
State: `ACTIVE OVERLAP REVIEW`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

```text
canonical issue: systemd/systemd#43214
active canonical PR: systemd/systemd#43217
active PR head checked: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled fork: teamleaderleo/systemd
controlled product branch: none
```

## Demonstrated mechanism

Repeated whitespace is preserved as empty fields because the bind parser treats colon and whitespace as separators under a no-coalescing extraction mode. Empty colon fields are meaningful; empty whitespace entries are not.

Installed Debian 13 systemd 257 reproduced empty-path warnings for repeated spaces and line-continuation indentation.

## Durable fixture

```text
investigations/systemd-bind-path-whitespace-overlap/reproduce.sh
```

It owns temporary-file cleanup and retains exact verifier inputs and outputs.

## First incomplete step

Execute the fixture against current canonical baseline and the exact PR #43217 head in disposable checkouts. Record:

- repository and file blobs;
- `systemd-analyze --version`;
- status and warnings;
- parsed bind-entry count if a unit test can expose it;
- serialization/deserialization round-trip;
- cleanup and rerun.

## Review warning

Do not evaluate the active PR only by whether the reported warning disappears. Its parser and execution-state changes require controls for meaningful empty colon fields, quoting, escaping, markers, reset behavior, and serialization.

## Publication boundary

No canonical comment or review is authorized. Retain findings internally until the user explicitly approves public communication.
