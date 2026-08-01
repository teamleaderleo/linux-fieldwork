# Upstream issue draft

Status: retained draft only; external posting is unauthorized.

## Title

tarfilter REGTYPE exclusion retains NUL-flagged regular members

## Body

`tarfilter --type-exclude=REGTYPE` currently maps the selector only to `tarfile.REGTYPE` (`b"0"`). Python also accepts `tarfile.AREGTYPE` (`b"\0"`) as an ordinary regular file, and `TarInfo.isfile()` returns true for both encodings.

The filter later compares each member's raw `type` byte against the stored selector bytes. As a result, a NUL-flagged regular member survives `--type-exclude=REGTYPE` and `--type-exclude=0` even though the member is handled as a regular file when its payload is copied.

A minimal archive contains:

- one `REGTYPE` regular member;
- one `AREGTYPE` regular member;
- one directory control.

On current upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94`, the selector still stores only `tarfile.REGTYPE`. On the executed baseline with the same relevant source bytes, `--type-exclude=REGTYPE` removes the `REGTYPE` member and retains the `AREGTYPE` member. The expected result removes both regular encodings and retains the directory.

The narrow correction maps `REGTYPE` and `0` to both accepted regular-file constants. A focused regression covers the baseline leak, both selector spellings, and an independent `DIRTYPE` control.

## Evidence to complete before posting

- exact materialized checkout and `tarfilter` blob at `77ec9be5417ee44c96343d2347145585da1b1f94`;
- current native test name and patch;
- baseline and candidate receipts through `coverage.py`;
- relevant broader test result;
- cleanup/rerun and complete-diff review.

## Authority

This draft has not been posted. Posting requires explicit authorization.
