# Handoff — cross-ecosystem candidate round

Handoff date: 2026-08-02  
State: `ACTIVE — JQ AND SYSTEMD RUNS QUEUED; UV DESIGN HOLD`  
External contact authorized: `false`  
External contact made: `none`

## Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
internal draft PR: #414
```

Resolve the live branch head before resuming because this branch is being updated by concurrent Fieldwork lanes.

## UV lock diagnostic

```text
repository: teamleaderleo/uv
source PR: #12
source head: ba55497fe83ea9bb07c04452f8ba190fa4440a05
state: HOLD / REPAIR
clean-source carrier PR: #15
clean-source focused run: 30754710006
parse-first experiment PR: #13
experiment head: f0673123cbabe859c12fe6baacc1fff872060f17
experiment run: 30755038821
```

### Current conclusion

The pre-parse source design has a real false positive: a valid requirements file `action.py.lock` is rejected whenever neighboring `action.py` is a valid PEP 723 script. Producer-compatible naming does not establish that a successfully parsed requirements file is a UV lockfile.

### Execution classification

- `30754710006`: failed only rustfmt on the exact pre-parse source; focused tests did not run. The source is mechanically fixable but semantically superseded.
- `30755038821`: failed before compilation because the runner-local parse-first patch no longer matched the exact repaired source. A fallback step also lacked the `rustfmt` component. No UV product result was executed.

### First incomplete step

Create a clean parse-first source transformation against `ba55497...` without brittle multiline replacement. Install rustfmt, enforce the changed-file fence, compile affected crates, and run producer-backed project/script/non-UTF-8 plus same-name valid requirements, missing-file and constraints controls.

Workspace: `investigations/uv-lock-requirements-diagnostic/`.

## WGPU/Naga f16 bitcast

```text
state: RETIRED — CURRENT NAGA ACCEPTS BOTH DIRECTIONS
controlled head: b39e1822d3317e1b2ab41108211adf048314fa7d
focused run: 30752907389
focused job: 91509997426
artifact: 8835144866
artifact digest: sha256:b507a9437f6f67de315317c79f4301b830388afd0072d66fcc5431a5615c8778
```

Exact matrix:

```text
scalar-control   status 0   accepted
vec-to-scalar    status 0   accepted
scalar-to-vec    status 0   accepted
```

All stdout files said `Validation successful`; stderr was empty. Ordinary WGPU workflows also passed. Internal WGPU PR #4 was closed without merge after the receipt was retained.

No next technical step exists for issue #8896 unless canonical source regresses.

Workspace: `investigations/wgpu-naga-f16-bitcast/`.

## jq destructuring path context

```text
canonical issue: jqlang/jq#3128
canonical commit: 603db3f57741d217ba651e61086b550a72148b83
closed prior attempt: jqlang/jq#3384
open equivalent PR: none found
controlled run: 30759608059
state at handoff update: queued
```

The matrix compares current source, the closed PR, and both unresolved `SUBEXP_END`/`POP` orders from the issue draft. Every row builds exact jq, runs seventeen semantic controls, retains disassembly, executes Valgrind discriminators, and runs complete `make check`.

The first workflow definition did not register because top-level concurrency referenced `matrix.variant`; commit `32570b31838f9f9d8a494e435a43b5f59de7cde6` repaired the carrier. Run `30759608059` is valid.

First incomplete step: read all four jobs and artifacts. Select no compiler layout from color alone.

Workspace: `investigations/jq-destructure-path-context/`.

## systemd bind-path whitespace overlap

```text
canonical issue: systemd/systemd#43214
active PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled run: 30759608071
state at handoff update: queued
```

Documentation review corrected the grammar assumption. Valid tuples are:

```text
source[:destination[:rbind|norbind]]
```

When destination is omitted, options must also be omitted. `source::norbind` is a documented invalid control.

The corrected fixture covers repeated/mixed/continued whitespace, valid source/destination/triple forms, quoting, escaped colons, ignore-missing and reset behavior, plus invalid omitted destination, extra fields and invalid options.

Run `30759608071` builds `systemd-analyze` from base and PR and executes the fixture. Parser output is only the first gate; execution-context serialization/deserialization remains required.

Workspace: `investigations/systemd-bind-path-whitespace-overlap/`.

## Screened overlaps and negative results

- OpenTelemetry JS #6967 → active canonical PR #6969.
- ripgrep #3222 → active canonical PR #3224 and duplicate.
- bat #3866, #3845, #3844, #3798 → active fixes already exist.
- fd #2067 and #2053 → active fixes already exist.
- Workerd #176 → obsolete against current caching.
- Execa apparent bugs → stale/closed; iterator docs not portable across supported Node versions.
- UV #15996 → active PR #19388.
- libarchive non-seekable 7-Zip → completed evidence with active overlap.

## Resume order

1. jq run `30759608059`: classify every layout and retain artifacts.
2. systemd run `30759608071`: classify build/parser results, then add the narrow serialization gate.
3. UV: replace the broken runner-local parse-first carrier with a clean exact-source experiment.
4. Continue discovery only after checking overlap; prefer one ownable source candidate over several duplicate reviews.

## Cleanup state

No local repository checkout survived because the runtime could not resolve `github.com`. Hosted workflows own build products and temporary cleanup. No credential, service, mount, device, or canonical upstream state was created.

## Publication boundary

All pull requests and workflows referenced here are internal or controlled-fork carriers. No canonical upstream communication has been authorized or made.
