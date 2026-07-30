# gpgvnoexpkeysig status-fd option validation

## Defect

`gpgvnoexpkeysig` runs under `set -eu`. Its scanner expands `$2` immediately after seeing `--status-fd`:

```sh
if [ "$1" = '--status-fd' ]; then
  echo "$2"
  return 0
fi
```

A bare trailing `--status-fd` therefore aborts through the shell's unset-positional-parameter path instead of the wrapper's controlled validation diagnostic.

The baseline scanner also ignores the common `--status-fd=N` spelling, returns the first separated occurrence without defining repeated-option precedence, and does not stop option discovery at `--`.

## Candidate

The retained POSIX-shell patch:

- defaults to descriptor 1 when no status option is present;
- accepts both `--status-fd N` and `--status-fd=N`;
- checks that a separated form has a following argument before expanding it;
- rejects empty, signed, alphanumeric, and otherwise non-decimal values before invoking gpgv;
- rejects the whole invocation if any status-fd occurrence is malformed;
- uses the last valid occurrence, matching ordinary command-line option precedence;
- stops wrapper option discovery at `--`, leaving later positional spellings untouched;
- retains the existing downstream numeric guard as defense in depth.

## Regression

`tests/test_mmdebstrap_gpgvnoexpkeysig_status_fd.py` applies the patch to an exact temporary source copy and uses a fake gpgv selected through a disposable PATH.

It requires:

- the baseline bare option to fail through its uncontrolled shell path;
- the candidate bare option to return 1 with `invalid --status-fd argument` and no shell `parameter not set` text;
- malformed separated and equals forms to reject before gpgv invocation;
- absent option status output to remain on stdout;
- valid separated and equals forms to write rewritten status to a real inherited descriptor;
- two valid occurrences to select only the last descriptor;
- a valid occurrence followed by a malformed one to reject the whole invocation and write to neither descriptor;
- both wrappers to pass `/bin/sh -n`.

`tests/test_mmdebstrap_gpgvnoexpkeysig_status_fd_end_options.py` separately proves:

- a positional `--status-fd` after `--` is not parsed by the wrapper;
- a valid selection before `--` remains authoritative when the same spelling appears positionally afterward.

## Boundary

This corrects option discovery and validation only. Verifier/filter status ownership and temporary status spooling are owned by issue #41 / PR #138. Normal verifier stdout versus explicit status-fd routing remains the imported pipeline's separate behavior until that topology is composed.

No external contact is included or authorized. Fixes #175.
