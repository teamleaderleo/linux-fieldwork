# mmdebstrap unwritable TMPDIR reproduction

## In simple words

`mmdebstrap` creates a temporary root directory while building a Debian filesystem. This probe checks what happens when a caller explicitly points `TMPDIR` at a directory they cannot write to. The suspected behavior is that `mmdebstrap` silently falls back to `/tmp`, which can put a large build on the wrong filesystem. The immediate goal is to capture the current behavior with the real executable before proposing any change.

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

The runner uses the imported executable with `--dry-run`, `--mode=unshare`, and `--variant=apt`. Dry-run initializes apt and exercises temporary-root selection without downloading or installing the root filesystem packages.

## Distinguishing outcomes

- **Silent fallback reproduced:** the requested directory is confirmed unwritable, the log selects `/tmp/mmdebstrap.*`, and no diagnostic identifies the unusable requested path.
- **Explicit failure or warning:** the command reports that the requested `TMPDIR` cannot be used.
- **Requested directory honored:** the selected temporary root is created below the requested path.
- **Blocked:** the GitHub runner fails before temporary-root selection, leaving the question unanswered.

## Stop condition

Stop after one GitHub-hosted Ubuntu run records the selected temporary directory, command status, full log, exact source revision, and whether a diagnostic mentions the unusable requested directory.

## Authority

This repository is owned by `teamleaderleo`. Upstream contact is not authorized by this experiment.
