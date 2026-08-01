# Upstream issue draft

Status: `NOT NEEDED`  
Proposed destination: canonical mmdebstrap Forgejo issue tracker, only if maintainers request issue-first discussion  
External contact authorized: `false`

## Decision

A separate issue is unnecessary for the current submission form. The pull-request draft contains the complete observed failure, source analysis, real reproducer, implementation, tests, compatibility boundary, and reviewer questions. Opening an issue as well would create two public carriers for the same bounded correction.

No issue was opened.

## Proposed title if issue-first discussion becomes required

`gpgvnoexpkeysig can mask verifier failure and delay wrapper-only cancellation`

## Draft

### Summary

`gpgvnoexpkeysig` currently filters GnuPG status output through a shell pipeline. The pipeline reports the filter's result, so `gpgv` can fail while the wrapper returns success. The same helper has incomplete `--status-fd` parsing and does not fully own verifier/filter cancellation and cleanup.

### Observed behavior

With the current helper, a real tampered detached signature produces:

```text
direct gpgv exit: 1
status: [GNUPG:] BADSIG ...
wrapper exit: 0
```

The status record survives, but the process result becomes the successful `sed` result.

A bare trailing `--status-fd` also expands a missing positional parameter under `set -u`. A signal delivered only to the wrapper can be deferred while a foreground verifier continues.

### Expected behavior

The wrapper preserves the verifier's ordinary result while rewriting only leading `EXPKEYSIG` records on the selected status descriptor. It validates supported status-fd forms before execution, owns and reaps verifier/filter children, forwards handled wrapper-only signals, cleans temporary state, and applies explicit verifier/filter/cleanup precedence.

### Minimal reproduction

1. Generate a signing key at a historical fake time with one-day expiry.
2. Sign a small APT-style `Release` file while the key is valid.
3. Verify today and confirm direct `gpgv` emits `EXPKEYSIG`.
4. Tamper the payload and compare direct `gpgv` with the wrapper using `--status-fd 3`.

Expected distinguishing result:

```text
direct tampered result: 1 with BADSIG
current wrapper result: 0 with BADSIG
corrected wrapper result: 1 with BADSIG
```

### Source analysis

The current helper ends with a POSIX shell pipeline equivalent to:

```sh
gpgv ... | sed 's/^\[GNUPG:\] EXPKEYSIG /[GNUPG:] GOODSIG /'
```

POSIX shell reports the final pipeline command's result. A live FIFO alternative allows an early filter failure to close the only reader and induce a writer-side failure in `gpgv`. Complete ownership therefore requires a separate verifier phase, completed status handoff, filter phase, child PID state, signal handling, and cleanup precedence.

### Evidence

On Linux x86_64 with GnuPG/gpgv 2.4.7 and APT 3.0.3:

- real expired signature: direct `gpgv` emitted `EXPKEYSIG`; corrected wrapper emitted `GOODSIG` and returned 0;
- real tampered signature: direct `gpgv` returned 1; current wrapper returned 0; corrected wrapper returned 1;
- isolated local `apt-get update` succeeded through the corrected `Apt::Key::gpgvcommand` path;
- candidate temporary directories were empty;
- the complete fixture passed immediately a second time.

### Compatibility and scope

The correction keeps `/bin/sh`, arbitrary numeric status descriptors, stdout/stderr separation, PATH lookup, and the exact `EXPKEYSIG` rewrite. Status output is buffered until verifier completion. Timeout/SIGKILL escalation, verifier descendants, and removal of dynamic-fd `eval` remain outside this change.

### Proposed direction

Use a private regular status file, separately owned verifier and filter children, pending-signal recording during launch/PID registration, durable filter-start state, explicit cleanup, and ordinary precedence of verifier failure, filter failure, cleanup failure, then success.

## Submission checklist

- [x] Current public issue and pull-request overlap checked on 2026-08-01.
- [x] Affected current upstream revision confirmed as `77ec9be5417ee44c96343d2347145585da1b1f94` with unchanged helper bytes.
- [x] Reproduction is minimal, disposable, and network-independent.
- [x] No private key, credential, or unsafe artifact is required.
- [x] Exact external destination identified.
- [ ] Explicit authorization recorded.
- [ ] Public issue reference and timestamp recorded, if an issue is later requested.
