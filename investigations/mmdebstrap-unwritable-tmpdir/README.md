# mmdebstrap explicit TMPDIR handling

## In simple words

`mmdebstrap` used to ignore an explicitly configured `TMPDIR` when that directory was unusable and silently place its temporary root under `/tmp`. The candidate now checks the configured directory before beginning the build. An unusable directory produces an immediate error naming the path; a usable directory continues to be honored and cleaned up.

## Question and answer

**Question:** When `TMPDIR` is explicitly set to an existing but unwritable directory, should `mmdebstrap` silently choose another filesystem?

**Candidate answer:** No. Treat the explicit value as a caller contract and fail before apt setup or root-filesystem creation.

## Source

- Project: Debian `mmdebstrap`
- Imported revision: `debian/1.5.7-3`
- Upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Candidate source commit: `927263e1a883e21573847da362456af637148868`
- Local source: `upstream/mmdebstrap/`

## Change

The candidate adds `check_tmpdir()` immediately after option parsing. When `TMPDIR` is non-empty, it:

1. requires the path to be a directory;
2. creates a small temporary file in that exact directory;
3. closes and removes the file;
4. reports a path-specific error when any step fails.

The imported test registry now includes `tests/fail-with-unwritable-tmpdir` alongside the existing successful custom-`TMPDIR` coverage.

## Verification

Run:

```sh
bash investigations/mmdebstrap-unwritable-tmpdir/run.sh
```

GitHub Actions run `30510240339` on Ubuntu 24.04.4 LTS verified both sides:

- an unwritable explicit `TMPDIR` exited nonzero, selected no fallback directory, and named the requested path in the diagnostic;
- a writable explicit `TMPDIR` completed with status 0, created its temporary root below the requested directory, and left no temporary files behind;
- `perl -c`, `sh -n`, and `bash -n` syntax checks passed.

## Evidence boundary

This verifies the candidate under the declared GitHub-hosted environment and the real `mmdebstrap` dry-run path in `chrootless` mode. The upstream test file is added and syntax-checked; the complete Debian test matrix has not been run in this repository.

## Authority

This work modifies only `teamleaderleo/linux-fieldwork`. No Debian issue, email, merge request, or patch submission has been created.
