# mmdebstrap gpgv wrapper status propagation

## In simple words

`gpgvnoexpkeysig` filters GnuPG status output through `sed`, but the shell pipeline returns `sed`'s status instead of `gpgv`'s. A verifier failure can therefore become wrapper status 0.

The local candidate gives the status stream its own FIFO, runs the filter in the background, captures the real verifier status, waits for the filter, and returns the verifier failure when one occurred.

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

## Candidate

The retained POSIX-shell patch:

1. creates a private temporary directory and FIFO;
2. starts only the `sed` status filter in the background;
3. redirects the selected dynamic GnuPG status fd into the FIFO;
4. runs `gpgv` in the foreground and captures its status;
5. waits for the filter and captures its status;
6. returns the verifier's nonzero status first, otherwise the filter status;
7. kills/reaps the filter and removes the FIFO/directory from the EXIT trap;
8. maps HUP, INT, and TERM to signal-derived shell exit codes before cleanup.

This avoids Bash process substitution and non-POSIX `pipefail` while preserving the existing `/bin/sh` interpreter.

## Regression matrix

- verifier 0 with `EXPKEYSIG` plus `BADSIG`: both baseline and candidate return 0, expiration is rewritten, bad-signature text is untouched;
- verifier 1 with `BADSIG`: baseline returns 0, candidate returns 1;
- verifier 2 with `EXPKEYSIG`: baseline returns 0, candidate returns 2 while retaining the intended text rewrite;
- verifier stderr remains stderr;
- baseline and candidate pass `/bin/sh -n`;
- each candidate run leaves its dedicated TMPDIR empty and no subprocess survives `subprocess.run()`.

## Severity

**Medium-high process-integrity boundary, approximately 6/10.**

APT also parses the GnuPG status stream, so common `BADSIG` records may still cause rejection. The process-status layer is nevertheless false: crashes, I/O failures, or unrecognized fatal verifier states can be masked if the filter exits normally.

The wrapper is installed and explicitly selectable as APT's `gpgvcommand`, but users opt into its deliberate expired-key weakening for historical snapshot access.

## Evidence limits

- The regression uses a fake verifier rather than real cryptographic fixtures.
- Statuses 0, 1, and 2 are covered; signal delivery is source-reviewed but not dynamically injected.
- The candidate keeps the current dynamic-fd `eval` mechanism; argument parsing/quoting outside this status boundary is unchanged.
- Accepting expired keys is the wrapper's documented purpose and is not reclassified as a defect here.

## Disposition

Retain the candidate and regression for internal review. No Debian or external upstream issue, patch, email, merge request, comment, or review is authorized or created.
