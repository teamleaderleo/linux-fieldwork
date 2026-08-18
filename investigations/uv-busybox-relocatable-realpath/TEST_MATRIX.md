# Test matrix — UV relocatable launchers on BusyBox

| Case | Invocation | Expected |
|---|---|---|
| Direct console script | Execute generated entrypoint by absolute path | Command succeeds; no `realpath: --` stderr |
| Relative console script | Execute `./bin/tool` | Correct interpreter selected; no stderr pollution |
| PATH lookup | Add environment `bin` to `PATH`, run basename | Correct interpreter selected |
| Symlinked entrypoint | Symlink tool outside environment and execute alias | Resolve original launcher and environment, preserving the historical symlink fix |
| Moved environment | Create relocatable environment, move directory, execute entrypoint | Interpreter path follows the moved environment |
| Space in environment path | Place environment under directory containing spaces | Launcher quoting remains correct |
| Leading-dash directory | Environment or alias path has a component beginning with `-` | Path remains an operand; no option confusion |
| Broken symlink | Invoke dangling alias | Clear existing failure behavior; no unrelated BusyBox diagnostic |
| BusyBox `ash` | Alpine/BusyBox userland | Clean execution |
| Debian `dash` + GNU tools | Conventional Linux userland | No regression |
| Bash | Bash-backed `/bin/sh` or direct shell fixture | No regression |
| macOS shell/userland | Supported macOS environment | No regression or documented platform-specific behavior |
| Relocatable activation | Source generated activation script after environment move | Correct environment root; clean stderr |
| Symlinked activation script | Source activation through a symlink when supported by shell semantics | Preserve intended root resolution or document existing boundary |

## Command-position controls

Test each delimiter independently:

1. current `dirname -- "$(realpath -- "$0")"`;
2. omit only `realpath --`;
3. omit only `dirname --`;
4. omit both;
5. any proposed shell-native alternative.

Do not infer that BusyBox behavior for `realpath` applies identically to `dirname`.

## Source gates

- exact canonical base and source blobs recorded;
- `cargo fmt --all --check`;
- affected crate compilation;
- unit test for exact generated launcher text where appropriate;
- integration execution on BusyBox/Alpine;
- existing relocatable symlink regression test retained;
- activation and console-script surfaces reviewed together;
- complete diff reviewed for unrelated shell-template changes.
