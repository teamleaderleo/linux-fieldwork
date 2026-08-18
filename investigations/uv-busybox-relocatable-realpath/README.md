# UV BusyBox relocatable `realpath` portability

State: `INVESTIGATED — SEPARATE SOURCE UNIT NOT YET CREATED`  
Canonical issue: `astral-sh/uv#16209`  
External contact authorized: `false`  
External contact made: `none`

## User problem

Relocatable UV console scripts embed a `/bin/sh` launcher containing:

```sh
"$(dirname -- "$(realpath -- "$0")")"/
```

BusyBox `realpath` does not treat `--` as an option delimiter. It interprets it as a path, emits `realpath: --: No such file or directory`, and then continues with the real script path. The console command can still succeed, but logs contain a misleading error and automation can treat unexpected stderr as a failure signal.

The issue has been reproduced in Alpine environments and remained open at the latest review.

## Historical constraint

`realpath` cannot simply be removed. UV added it after a symlink regression: invoking a relocatable entrypoint through a symlink must resolve the real launcher location before deriving the neighboring Python executable.

The required behavior is therefore:

- BusyBox-compatible invocation;
- symlinked entrypoints continue to locate the original environment;
- paths with spaces remain quoted correctly;
- relative invocation remains valid;
- moved relocatable environments continue to work;
- directory or script components beginning with `-` remain operands rather than options.

## Broader repository finding

The same portability surface exists beyond generated console scripts. UV's relocatable activation-script path also uses `realpath --` to resolve the activation file. A source repair limited to `uv-install-wheel/src/wheel.rs` risks leaving activation noisy or inconsistent.

Relevant source surfaces:

- `crates/uv-install-wheel/src/wheel.rs` — `format_shebang` for generated entrypoints;
- `crates/uv-virtualenv/src/virtualenv.rs` and activation templates — relocatable activation path handling;
- project and virtualenv integration tests covering relocation and symlink behavior.

## Initial compatibility experiment

A local BusyBox 1.37 shell experiment showed:

- `busybox realpath -- file` emits an error and returns failure while also printing the resolved path;
- `busybox realpath file` resolves the path cleanly;
- removing only the inner `realpath` delimiter preserved direct, relative, spaces, symlink, and leading-dash cases in the focused shell matrix.

That is directional evidence, not yet a UV source result. The outer `dirname --` has separate portability characteristics and should be tested rather than changed automatically.

## Candidate direction

The smallest plausible source repair is to omit `--` for `realpath` while retaining quoting and the `realpath` call itself. Before selecting it, compare supported shell/coreutils combinations and confirm UV's platform policy:

- Alpine / BusyBox;
- Debian or Ubuntu `/bin/sh` plus GNU coreutils;
- macOS userland where applicable;
- symlinked and moved environments.

A runtime flavor probe or generated-script branching would add complexity and should require evidence that unconditional omission breaks a supported case.

## Why this is useful

This is a small code surface with broad reach:

- Alpine is common in CI and containers;
- UV-generated scripts are user-facing artifacts executed outside UV itself;
- stderr pollution creates confusing logs even when the command succeeds;
- a complete repair can cover both console entrypoints and activation scripts while protecting the earlier symlink fix.

## Publication and overlap boundary

Keep this separate from the lockfile diagnostic. Search for a current canonical implementation before creating a source branch. Do not claim the naive “remove all `--`” solution; preserve the exact historical behavior and test every changed command position.

No canonical issue comment, pull request, or maintainer contact is authorized.
