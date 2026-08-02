# UV lockfile requirements diagnostic

State: `ACTIVE — SOURCE HELD FOR FALSE-POSITIVE REPAIR; CONTROLLED CI QUEUED`  
Canonical issue: `astral-sh/uv#16192`  
External contact authorized: `false`  
External contact made: `none`

## User problem

A user can reasonably pass a UV-generated lockfile to `uv pip install -r` while assuming that every dependency file produced by UV is requirements-compatible. The baseline instead feeds the TOML lockfile into the requirements parser and reports a low-level requirement syntax failure.

A direct diagnostic would explain the format mismatch and point the user back toward an exported `requirements.txt`. The value is reduced debugging time in local development and CI, especially for script lockfiles whose `<script-name>.lock` naming does not visibly identify TOML.

The diagnostic must preserve a more important invariant: `-r` means “parse this file as requirements.” The generic `.lock` suffix is also used for ordinary files, so UV must not reject a valid requirements file merely because its name resembles a UV output.

## Exact identities

```text
controlled repository: teamleaderleo/uv
controlled base: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
source branch: fieldwork/uv-lock-requirements-diagnostic
source head: ba55497fe83ea9bb07c04452f8ba190fa4440a05
internal source PR: teamleaderleo/uv#12

current-source execution PR: teamleaderleo/uv#15
current-source carrier head: b794c91c9bf50b2ee28cd588cd44e51eb44c1d09
current-source focused run: 30754710006 — queued at last check
current-source ordinary CI: 30754710091 — queued at last check

parse-failure experiment PR: teamleaderleo/uv#13
experiment carrier head: f0673123cbabe859c12fe6baacc1fff872060f17
experiment focused run: 30755038821 — queued at last check

canonical repository: astral-sh/uv
canonical head checked: 79bbface771210df216b738e9bdc7df95e5a9e6b
```

## Repository and historical findings

UV's lock target code establishes two producer identities:

- project lockfiles use the exact name `uv.lock`;
- script lockfiles append `.lock` to the script's complete native filename using `OsString`.

This matters for Unix filenames containing non-UTF-8 bytes. The current source generation repairs an earlier UTF-8-only detector and includes a producer-backed non-UTF-8 test.

A prior canonical attempt, `astral-sh/uv#16282`, inferred lock identity from TOML-looking contents. Review rejected that direction because unrelated files can contain the same strings. The current work does not inspect lockfile contents.

The parse layer in `uv-requirements/src/specification.rs` is shared by requirements, constraints, and overrides. A repair placed there must carry source provenance; otherwise a `-c` parse failure could receive an `-r`-specific message.

## Current source generation

Head `ba55497fe83ea9bb07c04452f8ba190fa4440a05` performs recognition in `RequirementsSource::from_requirements_txt`, before requirements parsing:

1. require the candidate path to exist;
2. recognize exact `uv.lock`;
3. for another final `.lock` extension, derive the complete sibling filename with `Path`/`OsStr` operations;
4. classify it only when the sibling parses as PEP 723 metadata;
5. leave an arbitrary `.lock` beside a non-PEP-723 sibling on the normal requirements path.

It has strong positive evidence design:

- project locks and script locks are generated through UV's real producers;
- a native non-UTF-8 script lock is generated on Unix;
- a `.lock` beside an ordinary script remains valid requirements input.

## Distinguishing defect found in review

The current detector still has a real false positive because classification precedes parsing.

```text
action.py       — valid PEP 723 script
action.py.lock  — independently valid requirements file, for example an empty file
```

`uv pip install -r action.py.lock` should preserve the explicit requirements interpretation. Current head rejects it solely because the neighboring script makes that filename one UV could also generate.

The existing success control uses a non-PEP-723 sibling, so it does not exercise this collision. Source PR #12 is now `HOLD / REPAIR` and its body records the counterexample.

## Parse-failure experiment

Execution PR #13 applies a bounded alternative to exact repaired source `ba55497...` inside the runner worktree:

1. add a requirements-file source variant carrying permission for the UV-lock diagnostic;
2. use that variant only for the explicit `-r` / requirements-file lane;
3. parse the file normally first;
4. only after parsing fails, test exact `uv.lock` or the exact PEP 723 sibling naming rule;
5. preserve ordinary errors for constraints and overrides;
6. retain `Path`/`OsStr` handling and all producer-backed tests.

Added distinguishing controls:

- valid empty `action.py.lock` beside valid PEP 723 `action.py` succeeds;
- missing `uv.lock` retains `File not found`;
- `-c action.py.lock` retains the requirements parser error and does not receive the `-r` diagnostic.

Run `30755038821` was queued at the last check. No compile or behavioral result is claimed yet.

## Compatibility boundary

Even the parse-first design cannot prove provenance for every invalid `.lock` file. An invalid arbitrary `action.py.lock` beside a valid PEP 723 script can receive the UV-lock hint because the file already failed requirements parsing and exactly matches a name UV generates. Avoiding that residual ambiguity would require format inspection or persistent provenance metadata, both outside this unit.

Other deferred surfaces:

- nested `-r` includes inside a requirements file;
- remote requirement URLs;
- symlink aliases that hide the original sibling relationship;
- stdin;
- positional package prompting;
- canonical routing while another upstream attempt exists.

## Separate UV opportunity

Issue `astral-sh/uv#16209` is a distinct Linux portability unit. Relocatable console scripts and activation scripts contain `realpath --`, which BusyBox treats differently. Historical code shows `realpath` was added to preserve symlinked relocatable entrypoints, so a correct patch must retain symlink, spaces, relative invocation, moved-environment, and leading-dash behavior. Keep that work separate from this diagnostic carrier.

## Cleanup and authority

No local checkout was created because the runtime could not resolve `github.com`. All source and evidence work occurred through the controlled GitHub connector and fork-local draft carriers. No canonical issue comment, pull request, maintainer message, or other upstream contact occurred.

## Next step

Read focused runs `30754710006` and `30755038821` by first failing owner. If the parse-first experiment passes formatting, affected-crate compilation, and all focused tests, revise the source branch to that scoped design and rerun from an exact clean carrier. If it fails, preserve the current source hold and record the first disproven assumption rather than broadening the patch.
