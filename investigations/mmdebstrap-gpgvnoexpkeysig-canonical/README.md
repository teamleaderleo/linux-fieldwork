# mmdebstrap `gpgvnoexpkeysig` canonical lifecycle

## In simple words

The imported wrapper has three connected defects: its pipeline can hide verifier failure, its `--status-fd` scan can abort or accept an incomplete option set, and a signal sent only to the wrapper can leave its verifier running.

This record carries one combined candidate. It validates every status-fd occurrence before execution, writes verifier status bytes to a private regular file, owns verifier and filter PIDs, closes child-launch registration windows with pending-signal traps, preserves completed status bytes on verifier cancellation, prevents completed filter output from being replayed by a late signal, and gives verifier, filter, cleanup, and signal results an explicit order.

## Source boundary

- initial repository base: `main` at `a254657636ca92302610cd4af4bc294fafa62bbd`;
- imported source: `upstream/mmdebstrap/gpgvnoexpkeysig`;
- imported blob: `83370755454a1322bf6862751aab7381d175aa8b`;
- combined patch: `0001-canonical-lifecycle.patch`;
- core regression: `tests/test_mmdebstrap_gpgvnoexpkeysig_canonical.py`;
- late-signal regression: `tests/test_mmdebstrap_gpgvnoexpkeysig_post_filter_signal.py`.

The initial construction host used `/usr/bin/dash` as `/bin/sh`, Python 3.13.5, GNU patch 2.8, git 2.47.3, and Linux 6.12.13 x86_64.

## Canonical decision

Use the combined patch as the sole landing candidate. The focused carriers remain useful evidence for how each defect was found, but they no longer need an ordered landing chain.

The candidate includes:

- PR #177's controlled parser behavior for `--status-fd N`, `--status-fd=N`, repeated occurrences, malformed occurrences, defaults, and `--`;
- PR #138's private regular status spool and verifier-over-filter ordinary status rule;
- PR #180's explicit verifier/filter ownership and signal forwarding goal;
- a replacement for PR #180's launch registration method: recording traps cover the interval between child creation and `$!` assignment, then any pending signal is dispatched after the PID is owned;
- an ordinary cleanup status path, so cleanup failure is visible after verifier and filter success;
- a durable filter-started state, so a signal after filter completion cannot replay the spool and duplicate status records.

## Candidate lifecycle

### Parser phase

The wrapper scans every status-fd occurrence before creating temporary state or invoking `gpgv`.

- absent option selects fd 1;
- both separated and equals spellings are accepted;
- the last valid occurrence selects the descriptor, matching real `gpgv` behavior already checked in PR #177;
- any malformed occurrence rejects the whole invocation;
- scanning stops at `--`.

### Verifier phase

The wrapper creates a private directory and regular status spool, then starts a background shell function that resets HUP/INT/TERM dispositions and `exec`s `gpgv`. The wrapper records the child PID and waits for it directly.

A regular file separates verifier execution from filter behavior. An immediate filter failure therefore cannot close a live transport or induce SIGPIPE in `gpgv`.

### Filter phase

After the verifier exits, a separately owned child reads the completed spool, rewrites only leading `EXPKEYSIG` records to `GOODSIG`, writes to the selected status descriptor, and is waited and cleared.

The wrapper marks the filter as started immediately after owning its PID. That state survives child exit and distinguishes “filter never started” from “filter finished and is no longer live.”

### Signal phase

During each child launch, temporary traps record a pending signal without starting cleanup. Once `$!` is stored, active traps are restored and any pending signal is handled with the owned PID.

HUP, INT, and TERM delivered only to the wrapper:

1. disable recursive signal handling;
2. forward the same signal to any live verifier or filter;
3. wait and clear both child PIDs;
4. when cancellation happened before filter launch, filter the completed non-empty spool once so flushed bytes remain available;
5. when the filter already started, preserve its existing output without replay;
6. attempt cleanup;
7. exit 129, 130, or 143.

## Review repair: signal after filter completion

The first combined head decided whether to replay the spool from filter liveness alone. A signal arriving after the filter exited but before ordinary cleanup completed found no live filter and ran the filter again, duplicating already-emitted status records.

The repaired candidate records whether filter execution ever started. A deterministic negative control blocks the first cleanup command after filter completion, sends SIGTERM to the wrapper, then releases cleanup while retaining the spool. The predecessor exits 143 after emitting the same rewritten record twice and invoking the filter twice. The repaired candidate exits 143 with one rewritten record, one filter invocation, and an empty TMPDIR.

## Result precedence

Ordinary execution uses:

```text
parser failure
  > verifier failure
  > filter failure
  > cleanup failure
  > success
```

The parser runs before temporary state and child execution. After execution begins, a nonzero verifier status wins over filter and cleanup status. Filter failure wins over cleanup failure. Cleanup failure is returned only after verifier and filter success.

A handled HUP/INT/TERM uses the signal-derived wrapper status. Filter and cleanup work in that path preserve bytes and remove state where possible; their statuses do not replace 129, 130, or 143.

## Executed gates

The initial eight-test matrix passed twice and Linux Fieldwork CI run `30578256280` passed at head `42eb8a683759d7f8ce342de7b1fb82f019667fc1`.

After the late-signal repair, Linux Fieldwork CI run `30578837652` passed at head `de8aa810d01866c13c386d3b75ae1f9f34430215`. Its repository unit suite includes the original eight-test matrix and the deterministic post-filter signal regression. Python compilation, shell syntax, and command-help gates passed; capture and privileged reproduction jobs skipped as intended.

The combined matrix proves:

- missing, empty, signed, alphanumeric, and malformed repeated status-fd forms fail before `gpgv` invocation;
- default, separated, equals, repeated-last, and `--` behavior route status bytes to the expected descriptor;
- verifier statuses 0, 1, and 2 survive filtering;
- an immediate filter status 7 after a status stream larger than ordinary pipe capacity returns 7 after verifier success and still returns 2 after verifier failure;
- cleanup status 9 is returned only after verifier/filter success;
- HUP, INT, and TERM sent only to the wrapper reach the verifier, return 129/130/143, preserve one rewritten flushed status record, reap the child, and empty TMPDIR;
- TERM during verifier launch registration leaves no orphan;
- TERM during filter launch registration leaves no orphan and emits no duplicate rewritten record;
- TERM during a blocking filter reaps the filter;
- TERM after filter completion emits no duplicate rewritten record;
- an immediate rerun after signal succeeds;
- every test run leaves its dedicated TMPDIR empty.

The three focused patches apply in the intended order on the exact imported source. Complete comparison against that stack shows the combined candidate retains the parser and regular-spool behavior while replacing the launch registration logic, adding cleanup precedence, and closing the late-filter replay race.

## Cleanup and rerun result

The regressions use dedicated temporary directories. Ordinary success, verifier failure, filter failure, cleanup failure simulation, steady-state signals, launch-window signals, active-filter signals, and post-filter signals leave no temporary child directory in the repaired candidate. Immediate reruns succeed.

## Evidence limits

- Fake verifier and filter executables isolate process, descriptor, and status behavior; no real cryptographic fixture or APT transaction was run.
- Signal forwarding waits for the child. A child that deliberately ignores the forwarded signal can delay wrapper exit; timeout, SIGKILL escalation, and verifier-created descendant process groups remain separate policy decisions.
- Status bytes are buffered until verifier completion. This preserves completed output and removes filter-to-verifier feedback, while changing live streaming behavior.
- Dynamic-fd redirection still uses the imported wrapper's `eval` approach.
- The candidate was executed on `/usr/bin/dash`; additional shell implementations remain useful compatibility checks before external submission.

## Carrier disposition

- PR #177: retain as parser evidence; retire as a landing carrier after the combined candidate lands.
- PR #138: retain as ordinary-status and regular-spool evidence; retire as a landing carrier after the combined candidate lands.
- PR #180: retain as signal-ownership evidence; retire as a landing carrier after the combined candidate lands.
- Issues #41, #175, and #176: route final review through the combined candidate.

## Disposition

Run exact-head CI once more after this tracked record update. If green, merge the combined candidate locally. No Debian issue, email, merge request, patch, comment, or review is authorized or created by this work.