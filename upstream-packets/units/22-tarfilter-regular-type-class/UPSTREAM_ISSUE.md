# Upstream issue draft

Status: retained draft only; external posting is unauthorized.

## Title

mmtarfilter REGTYPE exclusion retains NUL-flagged regular members

## Body

`mmtarfilter --type-exclude=REGTYPE` currently maps the selector only to `tarfile.REGTYPE` (`b"0"`). Python and GNU tar also recognize `tarfile.AREGTYPE` (`b"\0"`) as an ordinary regular file.

The filter later compares each member's raw `type` byte against the stored selector bytes. A NUL-flagged regular member therefore survives `--type-exclude=REGTYPE` and `--type-exclude=0`, even though the same member is classified and copied as a regular file.

A minimal archive contains:

- one `REGTYPE` regular member;
- one `AREGTYPE` regular member;
- one directory control.

On the affected baseline, `--type-exclude=REGTYPE` removes the `REGTYPE` member and retains the `AREGTYPE` member. The expected result removes both regular encodings and retains the directory.

The narrow correction maps `REGTYPE` and `0` to both regular-file constants. A focused native regression covers the baseline leak, both selector spellings, exact retained payloads, and an independent `DIRTYPE` control.

## Exact receipts required before posting

- base `77ec9be5417ee44c96343d2347145585da1b1f94` and tarfilter blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- controlled candidate head;
- focused upstream-native baseline/candidate result;
- relevant broader gate and cleanup/rerun;
- complete final diff and refreshed overlap search.

## Authority

This draft has not been posted. Posting requires explicit authorization.
