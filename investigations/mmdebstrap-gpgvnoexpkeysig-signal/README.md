# gpgvnoexpkeysig signal forwarding

## In simple words

The status-preserving wrapper candidate in PR #138 uses a private regular file so status filtering cannot interfere with verifier execution. It still runs `gpgv` as a foreground command, so a signal sent only to the wrapper can be deferred while `gpgv` continues.

This stacked candidate owns both child PIDs, forwards wrapper signals to the live child, reaps it, filters any completed status spool, and exits with the conventional signal-derived status.

## Canonical records

- Finding: #176
- Ordinary status repair: #41 / PR #138
- Imported source: `upstream/mmdebstrap/gpgvnoexpkeysig`
- Incremental patch: `0001-forward-signals-to-gpgv.patch`
- Regression: `tests/test_mmdebstrap_gpgvnoexpkeysig_signal.py`

## Candidate

After applying PR #138's regular-spool status patch, this candidate:

- tracks `GPGV_PID` and `FILTER_PID` independently;
- starts `gpgv` in the background and waits for its exact status;
- forwards HUP, INT, or TERM from the wrapper to a live verifier;
- waits for the verifier and clears its PID;
- if filtering had not started, launches `sed` over any non-empty completed status spool so already-flushed records are retained;
- if a signal arrives while the filter is already running, forwards the same signal and reaps it rather than starting a duplicate filter;
- clears both PID variables after `wait`;
- removes the status file and private directory;
- exits 129, 130, or 143 from the wrapper signal path;
- preserves ordinary verifier-over-filter status precedence.

The ordinary EXIT cleanup remains defensive: if the wrapper exits unexpectedly while either child remains, it stops and reaps both.

## Negative control and regression

A fake verifier writes and flushes an `EXPKEYSIG` status line to the selected status descriptor, records its PID, and then blocks.

The test sends SIGTERM only to the wrapper PID:

- PR #138 predecessor: wrapper and verifier remain alive after the signal;
- candidate: verifier receives TERM, the completed regular status spool is filtered, wrapper returns 143, output contains the rewritten `GOODSIG`, no verifier survives, and TMPDIR is empty.

Separate status controls require ordinary verifier exits 0 and 2 to remain identical between predecessor and candidate. Exact temporary source copies apply both patches and pass `/bin/sh -n`.

## Cleanup and safety

All processes are local test children in new process groups. The predecessor negative control is forcibly reaped after demonstrating delayed cancellation. Every file lives under `TemporaryDirectory`; no real keyring, APT operation, network, package mutation, or persistent path is used.

## Evidence boundary

This candidate forwards the requested signal and waits. It does not add a timeout or SIGKILL escalation when a verifier or filter deliberately ignores that signal, and it does not manage verifier-created descendant process groups. Those are separate forceful-cancellation policy decisions.

Filtering a completed spool during signal cleanup is bounded by the local filter process but not by an explicit timeout. The ordinary PR #138 candidate remains valid for callers that prefer deferred parent-only signals over extra child ownership.

## Disposition

Retain the stacked candidate and regression. No Debian or external upstream contact is included or authorized.
