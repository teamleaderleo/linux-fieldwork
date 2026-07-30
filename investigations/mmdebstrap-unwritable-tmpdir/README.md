# mmdebstrap unwritable TMPDIR reproduction

## In simple words

`mmdebstrap` creates a temporary root directory while building a Debian filesystem. This probe checks what happens when a caller explicitly points `TMPDIR` at a directory they cannot write to. The result is confirmed: at the imported revision, `mmdebstrap` silently falls back to `/tmp`, completes the dry-run, and never identifies the unusable requested directory.

## Question

When `TMPDIR` is explicitly set to an existing but unwritable directory, does `mmdebstrap` report the problem or silently create its temporary root under `/tmp`?

## Source

- Project: Debian `mmdebstrap`
- Imported revision: `debian/1.5.7-3`
- Resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Local source: `upstream/mmdebstrap/`

## Command

```sh
bash investigations/mmdebstrap-unwritable-tmpdir/run.sh
```

The runner uses the imported executable with `--dry-run`, `--mode=chrootless`, and `--variant=apt`. Dry-run initializes apt and exercises temporary-root selection without downloading or installing the root filesystem packages. Chrootless mode avoids the hosted runner's blocked user-namespace operation while preserving the tarball temporary-root path under study.

## Result

GitHub Actions run `30509181216` completed successfully on Ubuntu 24.04.4 LTS.

- The probe confirmed that the invoking user could not write to the requested `TMPDIR`.
- `mmdebstrap` selected `/tmp/mmdebstrap.xZqT2ZRG4w` instead.
- No diagnostic named or explained the unusable requested directory.
- The simulated apt and tarball path completed with status `0`.
- `mmdebstrap` removed the fallback directory during cleanup.

Retained evidence:

- `results/summary.json`
- `results/mmdebstrap.log`
- `results/notes.md`

## Evidence boundary

This establishes the behavior of revision `6fde999741f4fe1e7bf38079acf29432ef87a35e` under the declared GitHub-hosted Ubuntu environment. It does not decide whether the preferred change is an error, a warning, or documented fallback behavior.

## Stop condition

Met. The repository now retains the selected temporary directory, command status, full program log, exact source revision, environment, blocked first attempt, and diagnostic check.

## Authority

This repository is owned by `teamleaderleo`. Upstream contact is not authorized by this experiment.
