# Result

## In simple words

The original `mmdebstrap` revision silently treated an unusable explicit `TMPDIR` as permission to choose `/tmp`. The reviewed implementation now uses a non-empty explicit value as the exact parent at the real `File::Temp::tempdir()` call. Unset and empty values keep the old default behavior.

## Environment

- Deep verification run: `30512275538`
- Job: `90774688348`
- Runner: GitHub-hosted Ubuntu 24.04.4 LTS
- Imported upstream revision: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Reviewed Linux Fieldwork implementation: `c7f586470c34ca21a94a15ff340b3eca067f6ce5`
- Mode: `chrootless`
- Variant: `apt`
- Operation: real `mmdebstrap` dry-run with null output

## Behavior cases

| TMPDIR state | Status | Selected root | Result |
| --- | ---: | --- | --- |
| Unset | 0 | `/tmp/mmdebstrap.*` | Existing default preserved |
| Empty | 0 | `/tmp/mmdebstrap.*` | Existing default preserved |
| Writable directory | 0 | Below requested directory | Honored and cleaned |
| Unwritable directory | 13 | None | Rejected with path-specific error |
| Missing path | 2 | None | Rejected with path-specific error |
| Regular file | 25 | None | Rejected with path-specific error |

The nonzero status varies with the underlying filesystem failure. The stable contract is that an unusable non-empty explicit path fails, names that path, and does not select a fallback root.

## Static review

- Perl syntax: passed
- Reviewed source block: exact expected form
- Perl::Critic severity 4: passed
- Maximum code line length: 79
- POD rendering: passed
- Rendered regression test ShellCheck: passed
- Rendered regression test `shfmt`: passed
- Runner perltidy: v20230309
- Whole-file perltidy comparison: not treated as portable across formatter versions; the imported source marks sections for perltidy 20220613

## Suite inventory

- Test definitions: 120
- Test files: 120
- Test-script lines: 3,501
- Expanded matrix cases: 283
- Potentially runnable cases on amd64 after static skips: 274
- Definitions needing root: 45
- Definitions needing QEMU: 22
- Definitions needing isolated apt configuration: 27

The complete suite was not executed. See `suite-inventory.md` and `suite-inventory.json`.

## Interpretation

The reviewed implementation is smaller and more direct than the preliminary preflight helper. It uses the library's exact-directory interface at the operation that needs the directory, avoids a check-then-use interval, and keeps default behavior for callers who did not supply a non-empty value.

The practical trigger is narrow and its frequency is unknown. The impact is meaningful for affected callers because the temporary directory contains the working Debian root filesystem. Silent fallback can consume an unexpected disk or a small RAM-backed `/tmp` and can lead to a later out-of-space failure.

## Authority

No Debian issue, email, merge request, patch submission, comment, or review was created.
