# UV lockfile requirements diagnostic

State: `ACTIVE — CANDIDATE IN CONTROLLED CI`  
Canonical issue: `astral-sh/uv#16192`  
External contact authorized: `false`  
External contact made: `none`

## Question

When a user passes a UV-generated lockfile to `uv pip install -r`, can UV detect its own file type and emit a direct diagnostic without misclassifying arbitrary `.lock` requirements files?

## Baseline behavior

The issue reproducer passes a script lock such as `action.py.lock` through `-r`. Baseline UV treats the file as requirements syntax and reports a misleading requirement-parser failure from the lockfile's TOML.

A prior upstream PR, `astral-sh/uv#16282`, attempted to recognize the file by scanning its contents for lockfile-looking TOML substrings. That approach could misclassify unrelated files and was rejected.

## Exact source identities

```text
controlled repository: teamleaderleo/uv
controlled base: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
candidate branch: fieldwork/uv-lock-requirements-diagnostic
candidate head: a67f97bec7782c6f60aceefb2a9bcd7045582015
internal draft PR: teamleaderleo/uv#12

canonical repository: astral-sh/uv
canonical head checked: 79bbface771210df216b738e9bdc7df95e5a9e6b
canonical and controlled-base sources.rs blob:
cf6218326b96db5ce40e1fae31a0803e2c65e437
```

The canonical `sources.rs` file was byte-identical to the controlled base at the time of review.

## Selected design

UV's own lock-target code generates:

- project lockfiles at exactly `uv.lock`;
- script lockfiles by appending `.lock` to the script's exact filename.

The candidate therefore:

1. requires the passed lock path to exist;
2. recognizes exact `uv.lock` directly;
3. for any other `.lock`, strips only the final `.lock` suffix;
4. reads the exact sibling filename;
5. classifies the lock only when the sibling parses through `uv_scripts::Pep723Metadata::parse`;
6. otherwise leaves the `.lock` file on the ordinary requirements path.

It never reads or guesses the lockfile format itself.

## Candidate delta

```text
3 changed files
99 additions
0 deletions
```

Files:

- `crates/uv-requirements/src/sources.rs`
- `crates/uv/tests/pip_install/main.rs`
- `crates/uv/tests/pip_install/uv_lock_requirements.rs`

Complete-diff review caught and removed three unrelated reconstructed doc-comment changes. The final compare contains no deletions and no unrelated source change.

## Distinguishing tests

The candidate adds three focused integration controls:

1. existing exact `uv.lock` is rejected with a UV-lockfile diagnostic;
2. existing `action.py.lock` with a valid PEP 723 sibling script is rejected with the same diagnostic;
3. existing `action.py.lock` with an ordinary non-PEP-723 sibling remains an empty requirements file and succeeds.

The third case prevents filename-suffix overreach.

## Current execution

```text
GitHub Actions run: 30752526287
state at handoff: queued
```

No test result is claimed before the exact run starts and completes.

## Compatibility boundary

The candidate intentionally covers `-r` requirements files only. It does not yet change constraints, overrides, positional package prompting, remote files, stdin, or non-existent paths.

Requiring the lock path to exist preserves the ordinary missing-file diagnostic for a missing `uv.lock`.

## Cleanup

No local checkout was created because the runtime could not resolve `github.com`. All writes occurred through the controlled GitHub connector. No process, package installation, credential, environment mutation, or external project state remains.

## Next step

Classify run `30752526287` by first failing owner:

- formatting or linting;
- compile/API assumption;
- snapshot mismatch;
- focused behavior mismatch;
- unrelated repository CI.

Repair only the owning layer, rerun on the exact head, and retain logs and artifact identities. Do not contact canonical upstream without explicit authorization.
