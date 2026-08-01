# Upstream pull request draft

Status: `READY FOR AUTHORIZATION`  
Proposed destination: canonical mmdebstrap Forgejo repository  
Proposed base branch: `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`  
Candidate branch or patch series: `NEEDS FORK` / `NEEDS BRANCH`; retained single patch produces helper blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`  
External contact authorized: `false`

## Proposed title

`gpgvnoexpkeysig: preserve verifier status and own the wrapper lifecycle`

## Draft

### Summary

This change preserved the real `gpgv` result while continuing to rewrite only `EXPKEYSIG` status records to `GOODSIG`. It also validated supported `--status-fd` forms before execution, owned and reaped verifier and filter children, forwarded wrapper-only HUP/INT/TERM, retained completed status bytes, prevented duplicate replay after late signals, cleaned private state, and applied explicit verifier/filter/cleanup precedence.

The previous implementation ended in a `gpgv | sed` pipeline. Under POSIX `/bin/sh`, the pipeline reports `sed`'s result, so a verifier failure can become wrapper success. The parser also expanded a missing value after a bare `--status-fd`, and foreground verifier execution delayed cancellation delivered only to the wrapper.

### Before

A real tampered detached signature produced this distinction:

```text
direct gpgv exit: 1
current wrapper exit: 0
status in both cases: [GNUPG:] BADSIG ...
```

The status record remained visible, but callers relying on the process result received success.

A bare trailing `--status-fd` exited through the shell's unset positional-parameter error. Wrapper-only signals could remain deferred while a blocking foreground verifier continued.

### After

The corrected wrapper returned the verifier's exact ordinary result. For the same tampered signature, direct `gpgv` and the wrapper both returned 1 and emitted the same `BADSIG` status record.

A genuinely expired fixture key still exercised the helper's intended behavior: direct `gpgv` emitted `EXPKEYSIG`, the wrapper emitted `GOODSIG`, and verification returned 0. An isolated local `apt-get update` using `Apt::Key::gpgvcommand` completed successfully.

Supported status-fd forms were validated before temporary state or child execution. The last valid occurrence before `--` selected the descriptor, matching `gpgv` behavior. HUP, INT, and TERM sent only to the wrapper were forwarded to owned children, which were waited and cleared before exit.

### Implementation

The helper now uses one explicit lifecycle:

1. parse and validate every `--status-fd N` and `--status-fd=N` occurrence;
2. create a private regular status spool;
3. install recording traps during verifier launch and PID registration;
4. wait for the verifier and retain its exact status;
5. launch an owned filter over completed status bytes;
6. record that filtering started so a later signal cannot replay output;
7. wait for the filter and remove private state;
8. return verifier failure, then filter failure, then cleanup failure, then success;
9. on handled HUP/INT/TERM, forward the signal, reap children, preserve completed status once, clean, and return 129/130/143.

A regular file was selected instead of a live FIFO because an early filter exit can close the only reader and induce SIGPIPE in a still-running verifier, changing the result the wrapper is meant to preserve.

The parser, verifier result, status handoff, signal ownership, filter state, and cleanup belong in one reviewable change because they share the same source block and every phase contributes to the final result invariant.

### Tests

Executed against the current unchanged helper bytes:

- retained patch applied cleanly without fuzz or offsets;
- baseline helper blob: `83370755454a1322bf6862751aab7381d175aa8b`;
- candidate helper blob: `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`;
- `/bin/sh -n` passed for baseline and candidate;
- GnuPG/gpgv 2.4.7 generated and verified a disposable historical expired key;
- direct `EXPKEYSIG` became wrapper `GOODSIG` with status 0;
- direct tampered-signature status 1 remained wrapper status 1, while the baseline returned 0;
- status remained on fd 3 with stdout separate;
- isolated APT 3.0.3 `update` against a local `file:` repository passed through the candidate wrapper;
- candidate temporary directories were empty;
- the complete fixture passed immediately a second time.

The existing focused lifecycle matrix also covered verifier statuses 0/1/2, missing/empty/malformed/repeated status-fd forms, early filter failure with output beyond ordinary pipe capacity, cleanup precedence, wrapper-only HUP/INT/TERM, verifier and filter launch/PID-registration windows, blocking-filter cancellation, late-filter duplicate replay, child reaping, and immediate rerun.

The broad mirror/chroot `coverage.sh` suite was not run for this packet. The focused helper and local APT transaction require no network, mount, chroot, or privileged state.

### Compatibility

The change retained:

- the `/bin/sh` interpreter;
- PATH lookup for `gpgv`;
- arbitrary numeric status descriptors and dynamic redirection;
- separation of GnuPG status, stdout, and stderr;
- the exact leading `EXPKEYSIG` to `GOODSIG` rewrite;
- ordinary success for a cryptographically valid signature made by an expired key.

Status records are buffered until verifier completion. The small interval between temporary-directory creation and final trap installation remains a focused review point. Timeout/SIGKILL escalation for signal-ignoring children, verifier-created descendant process groups, and removal of the inherited dynamic-fd `eval` technique remain outside this change.

### Related issue

No separate upstream issue has been opened. This pull request contains the complete reproducer and scope. An issue can be added if project workflow requires issue-first discussion.

## Proposed commits or patch order

1. `gpgvnoexpkeysig: preserve verifier status and own lifecycle`
2. `tests: cover real expired and invalid signatures through APT`

The source correction can remain one commit. The real fixture may be a second commit for review clarity.

## Reviewer notes

Please focus review on:

- the completion-buffered regular-file handoff versus live status streaming;
- the explicit result order: verifier, filter, cleanup, success;
- pending-signal recording around both child launch/PID-registration intervals;
- durable filter-start state preventing late replay;
- the documented interval between `mktemp -d` and final trap installation;
- whether upstream wants timeout/escalation policy kept separate.

## Submission checklist

- [x] Candidate applied to the current intended upstream base.
- [x] Complete source diff reviewed.
- [x] Baseline real-signature regression fails and candidate passes.
- [x] Focused real GnuPG and local APT integration pass.
- [x] Synthetic parser/status/signal lifecycle matrix passed at its exact canonical head.
- [x] Cleanup and immediate rerun pass.
- [x] Active equivalent work checked on 2026-08-01.
- [ ] Controlled fork and candidate branch created.
- [x] Draft contains no credentials or private key material.
- [ ] Explicit authorization recorded.
- [ ] Public pull request and exact submitted head recorded after submission.
