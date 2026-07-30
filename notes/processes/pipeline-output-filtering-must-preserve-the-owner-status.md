# Pipeline output filtering must preserve the owner process status

## In simple words

A pipeline has two independent results:

1. the bytes produced by the command that owns the operation;
2. whether that command succeeded.

Filtering the bytes through a second command must not silently replace the owner's exit status with the filter's.

## POSIX pipeline trap

```sh
verifier "$@" | sed 's/old/new/'
```

In POSIX shell, the pipeline status is the last command's status. If `verifier` exits 2 and `sed` cleanly reaches EOF, the shell reports 0.

`set -e` does not repair this. Portable `/bin/sh` has no standard `pipefail` option.

## Correct ownership question

Ask which process owns success:

- A log prettifier usually does not own the operation.
- A protocol transformer may own output validity but not the producer's underlying success.
- A cryptographic verifier definitely owns the verification result.

A wrapper can prefer producer failure, then filter failure:

```text
if producer failed: return producer status
else if filter failed: return filter status
else: return 0
```

## POSIX status handoff

One portable shape is:

1. create a private FIFO;
2. run the output filter reading that FIFO in the background;
3. run the owner command in the foreground with its selected output fd redirected to the FIFO;
4. capture the owner status;
5. wait for and capture the filter status;
6. clean up and apply the documented precedence.

This costs more code than a pipeline, so cleanup, signal behavior, FIFO ownership, and temporary-root safety need explicit tests.

Alternatives include:

- Bash process substitution when changing the interpreter is acceptable;
- a small helper program that multiplexes output and status;
- writing owner output to a temporary file, then filtering after completion when streaming is unnecessary.

## Validation shape

Use a fake owner that can independently choose output and status:

- owner 0, filter 0;
- owner 1, filter 0;
- owner 2, filter 0;
- owner 0 with a forced filter failure;
- signal interruption;
- stderr passthrough;
- cleanup of FIFO, temporary root, and filter process.

Check content and status separately. A text rewrite test alone cannot prove lifecycle correctness.

## Source and validation

This note was derived from issue #41 and `investigations/mmdebstrap-gpgvnoexpkeysig-status/README.md`. The executable regression is `tests/test_mmdebstrap_gpgvnoexpkeysig_status.py`.

No upstream contact is authorized or made by this note.
