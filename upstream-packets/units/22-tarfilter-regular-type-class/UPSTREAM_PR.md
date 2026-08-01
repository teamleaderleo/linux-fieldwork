# Upstream pull-request draft

Status: retained draft only; external submission is unauthorized.

## Title

tarfilter: treat NUL and 0 as regular-file types

## Summary

`--type-exclude=REGTYPE` and `--type-exclude=0` exclude both regular-file encodings recognized by Python and GNU tar: `REGTYPE` (`b"0"`) and legacy `AREGTYPE` (`b"\0"`).

## Problem

The selector previously stored only `tarfile.REGTYPE`. The filter compares raw member type bytes, so a NUL-flagged regular file survived regular-file exclusion even though `TarInfo.isfile()` and GNU tar classify it as a regular file and tarfilter copies its payload through the regular-file path.

## Change

The `REGTYPE | 0` parser case stores both accepted regular-file constants. Other type selectors and archive behavior remain unchanged.

## Tests

Added `tests/tarfilter-regular-type-class` and registered it in `coverage.txt`. The focused archive contains `REGTYPE`, `AREGTYPE`, and `DIRTYPE` members and verifies:

- the affected baseline leaks the `AREGTYPE` member under `REGTYPE` exclusion;
- the candidate excludes both regular encodings for `REGTYPE` and `0`;
- the directory remains under regular exclusion;
- `DIRTYPE` exclusion retains both regular encodings and their exact payloads.

The retained Linux Fieldwork integration gate checks the exact source blob, requires baseline failure, applies the source patch with GNU patch `--fuzz=0`, and requires two candidate passes.

## Exact receipts required before submission

```text
Base commit: 77ec9be5417ee44c96343d2347145585da1b1f94
Base tarfilter blob: ad776167a8473d5d15dbe22e850f4f6db35cf278
Candidate head: <controlled fork commit>
Focused native test: <command and result>
Relevant broader gate: <command and result>
Cleanup/rerun: <result>
Complete diff: <review receipt>
Overlap refresh: <result>
```

## Scope

This pull request changes regular selector membership only. Hard-link dependency handling, transforms, path/PAX metadata, passthrough bytes, ID shifting, dotfile normalization, and parent metadata remain separate work.

## Authority

This draft has not been submitted. Creating an upstream fork, branch, pull request, comment, or review requires explicit authorization.
