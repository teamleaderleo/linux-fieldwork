# Result

## In simple words

The original `mmdebstrap` revision silently ignored an explicitly configured but unwritable `TMPDIR` and used `/tmp`. The candidate now rejects that configuration before creating the temporary root. A writable explicit directory still works and is left empty after cleanup.

## Environment

- Verification run: `30510240339`
- Job: `90768531961`
- Runner: GitHub-hosted Ubuntu 24.04.4 LTS
- Imported upstream revision: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Candidate source commit: `927263e1a883e21573847da362456af637148868`
- Mode: `chrootless`
- Variant: `apt`
- Operation: real `mmdebstrap` dry-run with null output

## Unwritable case

- Requested `TMPDIR`: `/home/runner/work/_temp/linux-fieldwork-mmdebstrap-tmpdir/unwritable`
- Command status: `25`
- Selected temporary root: none
- Diagnostic: `cannot use TMPDIR` followed by the exact requested path and `Permission denied`
- Result: rejected before apt setup and temporary-root fallback

## Writable case

- Requested `TMPDIR`: `/home/runner/work/_temp/linux-fieldwork-mmdebstrap-tmpdir/writable`
- Command status: `0`
- Selected temporary root: `/home/runner/work/_temp/linux-fieldwork-mmdebstrap-tmpdir/writable/mmdebstrap.fE8Jq8ztSf`
- Cleanup: complete; no files remained below the requested directory
- Result: explicit usable directory honored

## Candidate

The executable now validates a non-empty explicit `TMPDIR` by creating, closing, and removing a small temporary file in that exact directory. Failure produces a path-specific error. The imported upstream test registry includes `fail-with-unwritable-tmpdir` in `chrootless` mode.

## Verification status

- Perl syntax: passed
- Upstream regression-script shell syntax: passed
- Fieldwork runner shell syntax: passed
- Focused runtime regression: passed
- Full Debian test matrix: not run

## Authority

No Debian issue, email, merge request, comment, or patch submission was created.
