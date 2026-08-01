# Upstream issue draft

Status: retained draft only; external posting is unauthorized.

## Title

mmtarfilter REGTYPE exclusion retains NUL-flagged regular members

## Body

`mmtarfilter --type-exclude=REGTYPE` currently maps the selector only to `tarfile.REGTYPE` (`b"0"`). Python also accepts `tarfile.AREGTYPE` (`b"\0"`) as an ordinary regular file, and `TarInfo.isfile()` returns true for both encodings.

The filter later compares each member's raw `type` byte against the stored selector bytes. As a result, a NUL-flagged regular member survives `--type-exclude=REGTYPE` and `--type-exclude=0` even though the member is handled as a regular file when its payload is copied.

A minimal archive contains:

- one `REGTYPE` regular member;
- one `AREGTYPE` regular member;
- one directory control.

On the current affected baseline, `--type-exclude=REGTYPE` removes the `REGTYPE` member and retains the `AREGTYPE` member. The expected result removes both regular encodings and retains the directory.

The narrow correction maps `REGTYPE` and `0` to both accepted regular-file constants. A focused regression should cover the baseline leak, both selector spellings, and an independent `DIRTYPE` control.

## Evidence to refresh before posting

- exact current Salsa base commit and `tarfilter` blob;
- current native test file and command;
- baseline and candidate receipts on that exact base;
- relevant broader test result;
- final patch identity after tarfilter-series ordering.

## Authority

This draft has not been posted. Posting requires explicit authorization.
