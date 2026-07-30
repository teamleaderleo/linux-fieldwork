# mmdebstrap suite inventory

## In simple words

The source suite is much larger than the one focused TMPDIR check. It contains 120 named test scripts that expand into 283 distribution, mode, variant, and output-format cases before runtime filters. On amd64, 274 cases remain after the skip expressions that can be evaluated without running them.

## Inventory

- Registered test definitions: 120
- Test files: 120
- Aggregate lines across test scripts: 3,501
- Generated matrix cases: 283
- Statically skipped cases on amd64: 9
- Potentially runnable cases on amd64: 274
- Definitions needing root: 45
- Definitions needing QEMU: 22
- Definitions needing an isolated apt configuration: 27
- Main executable lines before embedded POD documentation: 7,589
- Main executable total lines including POD: 9,146

## Largest matrix expansions

- `check-for-bit-by-bit-identical-format-output`: 48 cases
- `create-tarball-dry-run`: 40 cases
- `mmdebstrap`: 24 cases
- `debootstrap`: 12 cases
- `check-against-debootstrap-dist`: 12 cases

## Runtime interpretation

The matrix size does not directly predict wall-clock time. Some cases are small command checks, while others build real Debian roots, compare output, use multiple modes or formats, or boot through QEMU. The suite requires a prepared local mirror. `coverage.py` records every case duration and the total runtime when the suite is actually run.

The complete suite was not run in Linux Fieldwork. The focused six-case TMPDIR review, static analysis, suite inventory, dependency installation, and artifact upload completed in about 34 seconds on a GitHub-hosted Ubuntu 24.04 runner. That timing is not an estimate for the complete source suite.

## Reproduction

```sh
python3 investigations/mmdebstrap-unwritable-tmpdir/suite_inventory.py
```

The machine-readable result is `suite-inventory.json`.
