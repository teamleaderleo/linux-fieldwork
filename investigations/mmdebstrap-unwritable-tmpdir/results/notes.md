# Result

## In simple words

The caller supplied an existing directory through `TMPDIR`, and the probe confirmed that the caller could not write there. `mmdebstrap` did not report that condition. It created its temporary root under `/tmp`, completed the dry-run successfully, and removed the fallback directory during cleanup.

## Environment

- GitHub Actions run: `30509181216`
- Job: `90765352097`
- Runner: GitHub-hosted Ubuntu 24.04.4 LTS
- Imported source revision: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Mode: `chrootless`
- Variant: `apt`
- Operation: dry-run with null output

## Observation

- Requested `TMPDIR`: `/home/runner/work/_temp/linux-fieldwork-mmdebstrap-tmpdir/unwritable`
- Requested directory writable by the invoking user: no
- Selected temporary root: `/tmp/mmdebstrap.xZqT2ZRG4w`
- Diagnostic naming the unusable requested directory: none
- Command status: `0`
- Cleanup: selected fallback directory removed

## Conclusion

At this revision and under the declared environment, an explicitly configured but unwritable `TMPDIR` is silently replaced with a `/tmp/mmdebstrap.*` directory. This establishes the local program behavior. It does not yet decide whether upstream should fail, warn, or retain fallback behavior.

## Earlier blocked attempt

The first attempt used `--mode=unshare`. The hosted runner failed during user-namespace setup before temporary-root selection with `setgid failed: Operation not permitted`. The retained result therefore uses `chrootless`, which reaches the same tarball temporary-root selection code without requiring the blocked namespace operation.

## Authority

No upstream issue, message, merge request, or patch submission was created.
