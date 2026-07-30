# LF-02 D-Bus result classification

## In simple words

The first privileged-host integration summary treated any traced `Permission denied` text as a logind `AccessDenied` result. That was too broad: filesystem `EACCES` lines from unrelated target paths were enough to set `logind_access_denied: true` even when no logind call occurred.

This note records the corrected parser contract for issue #97.

## Source boundary

- Investigation: PR #22
- Reviewed investigation head: `ce2ccfa75efef0ffb4b678e97633179c38e14ada`
- Classifier fix branch: `fix/lf-02-logind-result-classifier`
- Runner: `run.sh`
- Summary implementation: `summarize_results.py`
- Regression: `tests/test_lf02_privileged_summary.py`

## Original classification defect

The trace collector selected all lines matching:

```text
SCM_RIGHTS|AccessDenied|Permission denied
```

The summary then classified either `AccessDenied` or generic `Permission denied` as a logind access denial.

That incorrectly attributed unrelated lines such as:

```text
newfstatat(... "/target/var/lib/apt/lists/partial", ...) = -1 EACCES (Permission denied)
```

In retained evidence, the no-inhibit and isolated cases had empty logind-message files but still reported `logind_access_denied: true`.

## Corrected contract

The summary now distinguishes four outcomes:

| `logind_result` | Meaning |
|---|---|
| `not-observed` | no `org.freedesktop.login1` `Inhibit` message was observed |
| `inhibitor-fd-received` | the logind call was observed and the reply carried `SCM_RIGHTS` |
| `access-denied` | the logind call was observed and an explicit D-Bus `AccessDenied` marker was present |
| `response-unclassified` | a logind call was observed, but neither success nor explicit denial was identified |

The compatibility boolean `logind_access_denied` remains, but it is true only when both conditions hold:

1. an `org.freedesktop.login1` `Inhibit` message is present;
2. the result contains an explicit `AccessDenied` marker.

Generic filesystem `Permission denied` text is no longer collected as a D-Bus result and cannot set this boolean.

## Regression matrix

The unit regression covers:

- unrelated `newfstatat(... EACCES (Permission denied))` with no logind call: `not-observed`, access denied false;
- explicit `org.freedesktop.DBus.Error.AccessDenied` after a logind inhibit call: `access-denied`, boolean true;
- successful `SCM_RIGHTS` inhibitor-FD reply: `inhibitor-fd-received`, access denied false;
- bare `AccessDenied` text without a logind call: not attributed to logind.

The full privileged matrix remains responsible for proving the real default, no-inhibit, and isolated host-service behavior.

## Schema note

The corrected summary sets `schema_version: 2` and adds `logind_result` while retaining existing booleans. Consumers should prefer the enum for interpretation and treat old schema-1 `logind_access_denied` values as unreliable when they were derived from generic `Permission denied` text.

## Expected corrected retained matrix

Based on the retained traces:

- `default-root`: `inhibitor-fd-received`, access denied false;
- `no-inhibit-root`: `not-observed`, access denied false;
- `isolated-root`: `not-observed`, access denied false.

These expectations remain provisional until the exact-head workflow regenerates the matrix.

## Evidence limits

- `strace` string capture is still a heuristic view of D-Bus messages, not a protocol decoder.
- An explicit D-Bus monitor or structured client trace would be stronger if later work needs to classify additional error types.
- The current correction is intentionally narrow: stop false attribution and expose an unclassified state instead of guessing.

## Authority

Internal Linux Fieldwork correction only. No upstream contact.
