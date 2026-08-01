# Deep dive

## Question and observed failure

Can `gpgvnoexpkeysig` relax only the expired-key status needed for historical APT repositories while preserving every unrelated verifier result and owning its complete child lifecycle?

The imported helper ends in `gpgv | sed`. Under `/bin/sh`, the pipeline result is the final `sed` result. Synthetic fixtures established that verifier statuses 1 and 2 can become wrapper status 0. The new real fixture confirms the same defect with GnuPG 2.4.7: a tampered APT-style `Release` file makes direct `gpgv` return 1 with `BADSIG`, the baseline wrapper returns 0, and the candidate returns 1 with the same `BADSIG` record.

This is a source-owner defect. The same keyring, detached signature, payload, descriptor routing, GnuPG executable, and environment are used for direct, baseline, and candidate runs. Only the wrapper implementation changes.

## Source mechanism

The baseline scans for the first separated `--status-fd`, then runs an `eval`-constructed pipeline:

```sh
gpgv "$@" STATUSFD>&1 | sed 'EXPKEYSIG -> GOODSIG' >&STATUSFD
```

That single line couples four independent results:

1. option parsing;
2. verifier execution;
3. status-byte transport and filtering;
4. process status returned to APT.

The shell reports `sed`'s result. A live FIFO replacement also couples filter liveness back into the verifier: an early filter exit can close the only reader and induce SIGPIPE in `gpgv`. Keeping `gpgv` in the foreground preserves ordinary status but allows wrapper-only signals to remain deferred. Backgrounding it without protecting the interval before `$!` registration creates an orphan window. Replaying a completed spool based only on filter liveness creates a late-signal duplicate-output window.

PR #196 resolves the complete chain with explicit phase state.

## Reproduction narrative

The committed fixture contains APT-style `Release` metadata. The runner:

1. copies the imported helper into a disposable source tree;
2. applies the retained canonical patch and asserts the exact baseline and candidate Git blob identities;
3. generates an RSA signing key at fake time 2000-01-01 with one-day expiry;
4. signs the metadata one hour later;
5. verifies today, causing real `gpgv` to emit `KEYEXPIRED` and `EXPKEYSIG`;
6. runs direct `gpgv`, baseline wrapper, and candidate wrapper through status fd 3;
7. tampers the payload and repeats the three verifier runs;
8. creates a minimal local APT repository, clear-signs `InRelease` with the expired key, and runs isolated `apt-get update` through both wrappers;
9. checks temporary-directory emptiness;
10. repeats the complete fixture immediately.

The expired signature remains cryptographically valid: direct `gpgv` returns 0 and emits `EXPKEYSIG`. Both wrappers return 0 and emit `GOODSIG`. The tampered payload is the distinguishing control: direct `gpgv` returns 1, baseline returns 0, candidate returns 1. Both APT updates succeed through the intended `Apt::Key::gpgvcommand` interface.

## Approach history

### Approach A — retain the pipeline with Bash status helpers

- Mechanism: use `PIPESTATUS` or `set -o pipefail`.
- Evidence: target interpreter is `/bin/sh` with `dash`; these are outside the portable contract.
- Result: rejected.
- Compatibility cost: changes interpreter requirements and still leaves parser, descriptor, child, signal, and cleanup ownership unresolved.

### Approach B — live FIFO between verifier and filter

- Mechanism: capture verifier status separately while streaming status records.
- Evidence: PR #138 review used an immediate filter failure and output exceeding pipe capacity. Closing the only reader induced a writer-side failure and changed verifier behavior.
- Result: rejected.
- Compatibility cost: filter failure can mutate the verifier result, defeating the desired precedence.

### Approach C — foreground verifier plus regular spool

- Mechanism: write status to a private regular file, wait for verifier, then filter.
- Evidence: ordinary statuses 0/1/2 and early-filter controls passed; wrapper-only TERM remained deferred while a blocking verifier ran.
- Result: accepted as the ordinary-status mechanism and superseded as the complete lifecycle.
- Compatibility cost: status bytes are buffered until verifier completion.

### Approach D — background verifier with direct PID assignment

- Mechanism: launch child in background, then assign `$!`, forward signals, and reap.
- Evidence: PR #180 review identified a signal window between child creation and PID registration for both verifier and filter.
- Result: superseded.
- Compatibility cost: unrecorded children or duplicate filtering can occur in that window.

### Approach E — composed lifecycle with recording traps

- Mechanism: temporary traps record pending signal identity during each launch; after `$!` is stored, active forwarding traps resume and dispatch any pending signal. A regular spool separates verifier and filter. Durable `FILTER_STARTED` state prevents late replay.
- Evidence: PR #196's canonical matrix covered both launch windows, steady-state HUP/INT/TERM, blocking filter, cleanup, and late-filter replay. The real fixture adds actual GnuPG and APT behavior.
- Result: selected.
- Compatibility cost: buffered status, retained `eval`, and no force-kill policy.

## Selected correction

The candidate performs these phases:

1. parse and validate all status-fd occurrences before temporary state;
2. create a private directory and status file;
3. install recording traps, launch verifier, store PID, restore forwarding traps, dispatch pending signal;
4. wait and retain exact verifier status;
5. install recording traps, launch filter over completed bytes, store PID and mark filter started, restore forwarding traps, dispatch pending signal;
6. wait and retain filter status;
7. remove status file and directory;
8. return verifier failure first, then filter failure, then cleanup failure;
9. for handled HUP/INT/TERM, forward, reap, preserve already-produced bytes once, clean, and return 129/130/143.

## Why the changes belong together

Parser output selects the descriptor used by both child phases. The verifier result controls ordinary precedence. The spool determines whether filter failure can alter verifier behavior. Signal handling needs both child PIDs, spool state, and filter-start state. Cleanup acts on state created by all earlier phases. Splitting these overlapping lines into independent public patches would recreate intermediate states with known lifecycle defects.

## Compatibility analysis

### Status bytes and descriptors

Only lines beginning exactly `[GNUPG:] EXPKEYSIG ` are rewritten. Other status records, including `BADSIG`, remain unchanged. The selected status descriptor remains separate from stdout and stderr. Both separated and equals status-fd forms are accepted, repeated valid options use the last occurrence, and scanning stops at `--`.

### Ordinary status and continuation

Verifier failure wins over filter and cleanup failure. Filter failure wins after verifier success. Cleanup failure is returned after both children succeed. Real `gpgv` status 1 survives the candidate.

### Signals and processes

The wrapper owns direct verifier and filter PIDs. Handled HUP/INT/TERM are forwarded and children are waited before exit. PID variables are cleared after wait to avoid signaling reused PIDs. Descendant process groups and forceful escalation remain outside the candidate.

### Files and cleanup

The status spool lives in a private `mktemp -d` directory under `${TMPDIR:-/tmp}`. Ordinary, failure, signal, and real-fixture cases remove the status file and directory. The tiny interval between directory creation and final trap installation remains documented.

### Environment and command lookup

The helper still resolves `gpgv` through `PATH`, checks command availability, and uses the inherited shell. The real fixture uses system `gpg`, `gpgv`, `apt-get`, `patch`, and standard digest utilities.

### APT integration

The isolated local repository uses `signed-by` and invokes the wrapper through `Apt::Key::gpgvcommand`. An expired but valid `InRelease` succeeds through both wrappers, confirming the selected descriptor and status rewrite are accepted by APT 3.0.3.

## Negative controls and losing mutations

- Real tampered payload: direct `gpgv` status 1; baseline wrapper 0; candidate 1.
- Direct expired-key verification: emits `EXPKEYSIG`, proving the fixture can observe the target record before rewriting.
- Baseline expired-key wrapper: emits `GOODSIG`, proving the historical behavior remains available.
- PR #138 early-filter mutation: live FIFO can feed failure back into verifier.
- PR #180 launch-window mutation: child can exist before PID ownership.
- PR #196 predecessor late-signal mutation: completed filter output can be emitted twice without durable `FILTER_STARTED` state.
- Immediate rerun: a stale key home, child, temporary path, or APT list lock would fail the repeated execution.

## Current upstream and historical review

The official repository displayed current `main` head `77ec9be5417ee44c96343d2347145585da1b1f94` on 2026-08-01. The helper's displayed latest change is `59e5870e7b76cc25dc6cb7b34586451d4ec2a524`, and its displayed implementation remains the same pipeline source imported as blob `83370755454a1322bf6862751aab7381d175aa8b`. The retained patch applies without offset or source edit and produces candidate blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`.

Indexed searches for the helper name and `EXPKEYSIG` found no equivalent active upstream issue or pull request. Public overlap must be refreshed immediately before submission.

## Remaining questions

1. **Regular-file buffering tradeoff.** Discriminator: upstream maintainer preference after reviewing the real fixture and expected status volume.
2. **Pre-trap temporary-directory interval.** Discriminator: an accepted POSIX-shell mechanism that installs cleanup ownership before or atomically with directory creation without adding broader complexity.
3. **Signal-ignoring child policy.** Discriminator: an explicit upstream decision on grace period, SIGKILL escalation, and descendants.
4. **Submission form.** Discriminator: owner authorization to create a controlled fork and whether upstream prefers the composed patch or a review-friendly split that never exposes known-bad intermediate states.

## Evidence boundary

Demonstrated on Linux x86_64 with `/bin/sh` syntax through `dash`, GnuPG/gpgv 2.4.7, APT 3.0.3, and disposable unprivileged file/key state. The complete synthetic matrix previously ran in Linux Fieldwork CI. The new real fixture ran twice locally and included a full local APT metadata update. No remote mirror, privileged chroot build, alternate shell, disk-full simulation, signal-ignoring child, or public upstream branch was exercised.

## Reopen triggers

- upstream helper bytes change after `77ec9be5417ee44c96343d2347145585da1b1f94`;
- an equivalent public issue or pull request appears;
- GnuPG or APT changes the status-fd or `EXPKEYSIG` contract;
- the fixture fails on a supported GnuPG/APT version;
- upstream rejects regular-file buffering;
- authorization expands to create the fork and public carrier;
- a new proof closes the pre-trap interval with lower complexity.
