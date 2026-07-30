# mmdebstrap gpgv wrapper status propagation

## In simple words

`gpgvnoexpkeysig` filters GnuPG status output through `sed`, but the shell pipeline returns `sed`'s status instead of `gpgv`'s. A verifier failure can therefore become wrapper status 0.

A first FIFO candidate captured the two statuses separately, but an early filter exit could close the only reader and induce SIGPIPE in a still-running verifier. The corrected candidate instead lets `gpgv` write its status stream to a private regular file, then runs the text filter only after the verifier has exited.

## Canonical records

- issue: #41
- source: `upstream/mmdebstrap/gpgvnoexpkeysig`
- imported blob: `83370755454a1322bf6862751aab7381d175aa8b`
- candidate: `0001-preserve-gpgv-status.patch`
- regression: `tests/test_mmdebstrap_gpgvnoexpkeysig_status.py`
- reusable note: `notes/processes/pipeline-output-filtering-must-preserve-the-owner-status.md`

## Exact baseline behavior

The final source line is:

```sh
eval 'exec gpgv "$@" ... | sed ...'
```

Under POSIX pipeline semantics, the pipeline status is the final command's status. `sed` can consume and rewrite a normal status stream successfully even when `gpgv` exits 1 or 2.

The wrapper's intended exception is narrow: transform status records beginning with `EXPKEYSIG` into `GOODSIG` so old snapshot signatures can be accepted despite expiration. Other verifier failures still need their original process status.

## Negative control

The regression places a fake `gpgv` first in a disposable `PATH`. The fake verifier emits caller-selected GnuPG status lines and exits with caller-selected status.

The exact imported wrapper must reproduce:

- fake status 1 -> wrapper status 0;
- fake status 2 -> wrapper status 0;
- `EXPKEYSIG` text still becomes `GOODSIG`;
- `BADSIG` text remains unchanged.

This isolates status masking from APT's separate interpretation of individual GnuPG status records.

## Corrected candidate

The retained POSIX-shell patch:

1. creates a private `0700` temporary directory with `mktemp -d`;
2. redirects the selected dynamic GnuPG status fd to a regular status spool inside that directory;
3. runs `gpgv` in the foreground and captures its real status;
4. only after the verifier exits, runs `sed` over the completed spool and captures the filter status;
5. returns the verifier's nonzero status first, otherwise the filter status;
6. removes the spool/directory from the EXIT trap;
7. maps HUP, INT, and TERM to conventional signal-derived shell exit codes after any foreground verifier deferral.

This avoids Bash process substitution and non-POSIX `pipefail` while preserving the existing `/bin/sh` interpreter. More importantly, the filter is no longer a live reader in the verifier's write path, so an immediate filter failure cannot mutate verifier behavior through SIGPIPE.

## Signal boundary

The verifier remains a foreground child. On the tested `/bin/sh`, a signal delivered only to the wrapper can be deferred while that child runs. The candidate does not claim prompt parent-only cancellation:

- parent-only TERM is shown to leave the foreground verifier running temporarily;
- after the verifier ends, the pending trap exits 143 and removes the status spool;
- process-group TERM reaches both shell and verifier, then the wrapper exits 143 with no survivor or temporary state.

This is an explicit eventual-cleanup boundary, not false prompt-child-ownership language.

## Regression matrix

- verifier 0 with `EXPKEYSIG` plus `BADSIG`: both baseline and candidate return 0, expiration is rewritten, bad-signature text is untouched;
- verifier 1 with `BADSIG`: baseline returns 0, candidate returns 1;
- verifier 2 with `EXPKEYSIG`: baseline returns 0, candidate returns 2 while retaining the intended text rewrite;
- an explicit non-stdout status fd remains separate from normal verifier stdout;
- an immediate filter exit 7 with a status stream larger than common pipe capacity returns 7 after verifier success and still returns verifier status 2 after verifier failure;
- parent-only TERM has the documented deferred behavior, then exits 143 and cleans;
- process-group TERM stops the verifier, exits 143, and cleans;
- verifier stderr remains stderr;
- baseline and candidate pass `/bin/sh -n`;
- each candidate run leaves its dedicated TMPDIR empty and no subprocess survives.

## Severity

**Medium-high process-integrity boundary, approximately 6/10.**

APT also parses the GnuPG status stream, so common `BADSIG` records may still cause rejection. The process-status layer is nevertheless false: crashes, I/O failures, or unrecognized fatal verifier states can be masked if the filter exits normally.

The wrapper is installed and explicitly selectable as APT's `gpgvcommand`, but users opt into its deliberate expired-key weakening for historical snapshot access.

## Evidence limits

- The regression uses a fake verifier rather than real cryptographic fixtures.
- Statuses 0, 1, 2, filter 7, and TERM delivery are covered.
- Status output is buffered until verifier completion instead of streamed live. APT's normal wrapper contract is completion-based, but interactive real-time status consumers remain outside this candidate.
- The candidate keeps the current dynamic-fd `eval` mechanism; argument parsing/quoting outside this status boundary is unchanged.
- Accepting expired keys is the wrapper's documented purpose and is not reclassified as a defect here.

## Disposition

Retain the candidate and regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
