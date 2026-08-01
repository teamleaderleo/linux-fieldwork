# Upstream merge-request draft

Status: retained draft only; external submission is unauthorized.

## Title

tarfilter: treat NUL and 0 as regular-file types

## Summary

`--type-exclude=REGTYPE` and `--type-exclude=0` now exclude both ordinary regular-file encodings accepted by Python's `tarfile` module: `REGTYPE` (`b"0"`) and legacy `AREGTYPE` (`b"\0"`).

## Problem

The selector previously stored only `tarfile.REGTYPE`. The filter compares raw member type bytes, so a NUL-flagged regular file survived regular-file exclusion even though `TarInfo.isfile()` classifies it as a regular file and tarfilter copies its payload through the regular-file path.

## Change

The `REGTYPE | 0` parser case stores both accepted regular-file constants. Other type selectors and archive behavior remain unchanged.

## Tests

The focused archive regression contains `REGTYPE`, `AREGTYPE`, and `DIRTYPE` members and verifies:

- the affected baseline leaks the `AREGTYPE` member under `REGTYPE` exclusion;
- the candidate excludes both regular encodings for `REGTYPE` and `0`;
- the directory remains under regular exclusion;
- `DIRTYPE` exclusion remains independent and retains both regular encodings.

## Before submission

Replace this section with exact current-upstream receipts:

```text
Base commit: <current Salsa master>
Candidate head: <controlled fork commit>
Focused test: <command and result>
Relevant broader gate: <command and result>
Cleanup/rerun: <result>
```

## Scope

This merge request changes regular selector membership only. Hard-link dependency handling, transforms, path/PAX metadata, passthrough bytes, ID shifting, dotfile normalization, and parent metadata remain separate work.

## Authority

This draft has not been submitted. Creating a fork, branch, merge request, comment, or review requires explicit authorization.
