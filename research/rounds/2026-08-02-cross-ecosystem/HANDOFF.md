# Handoff — cross-ecosystem candidate round

Handoff date: 2026-08-03  
State: `ACTIVE — JQ DEDICATED INDEX EXPERIMENT; SYSTEMD REPAIRED COMPARISON; UV DESIGN HOLD`  
External contact authorized: `false`  
External contact made: `none`

## Linux Fieldwork state

```text
repository: teamleaderleo/linux-fieldwork
branch: investigation/cross-ecosystem-round-2026-08-02
branch base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
internal draft PR: #414
```

Resolve the live branch head before resuming because this branch is shared by concurrent Fieldwork lanes. After this handoff update, do not infer focused run identity from older branch heads.

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

The pre-parse source design has a real false positive: a valid requirements file `action.py.lock` is rejected whenever neighboring `action.py` is a valid PEP 723 script. Producer-compatible naming does not establish that a successfully parsed requirements file is a UV lockfile.

Execution classification:

- `30754710006`: failed only rustfmt on the exact pre-parse source; focused tests did not run. The source is mechanically fixable but semantically superseded.
- `30755038821`: failed before compilation because the runner-local parse-first patch no longer matched the repaired source. Its fallback formatting step also lacked rustfmt. No UV product result was executed.

First incomplete step: create a clean parse-first transformation against `ba55497...` without brittle multiline replacement, install rustfmt, enforce the source fence, compile affected crates, and run producer-backed project/script/non-UTF-8 plus same-name valid requirements, missing-file, and constraint-routing controls.

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

The exact scalar, vector-to-scalar, and scalar-to-vector cases all passed. Ordinary WGPU workflows also passed. Internal WGPU PR #4 was closed without merge after the exact receipt was retained. No next technical step exists for issue #8896 unless canonical source regresses.

Workspace: `investigations/wgpu-naga-f16-bitcast/`.

## jq destructuring path context

### Completed four-layout matrix

```text
canonical issue: jqlang/jq#3128
canonical commit: 603db3f57741d217ba651e61086b550a72148b83
closed prior attempt: jqlang/jq#3384
open equivalent canonical PR: none found
Linux Fieldwork run: 30759715899
```

The complete result is retained at:

```text
research/rounds/2026-08-02-cross-ecosystem/jq-3128-four-layout-result.md
```

Classification:

1. canonical source reproduces the constant-value invalid-path error and passes the full suite;
2. closed PR #3384 fixes simple paths but breaks ordinary nested/array bindings, fails alternation, and fails `make check`;
3. delayed `SUBEXP_END` followed by `POP` preserves bindings but erases every matcher path to `[]`;
4. `POP` before delayed `SUBEXP_END` corrupts the runtime stack and aborts with status 134.

The final row exposed a carrier flaw: its Valgrind gate only treated statuses 97 and 124 as failures, so ordinary abort 134 was not classified by that step. The abort and six failed jq test groups are retained as the source of truth.

### Dedicated index experiment

```text
controlled fork: teamleaderleo/jq
branch: fieldwork/3128-destructure-index-path
head: 2b1f443fffbb1e629cc53ebef8884fcaa81a5a02
internal draft PR: #1
focused run: 30799146702
ordinary CI: 30799146647
oniguruma: 30799146694
decnum: 30799146753
valgrind: 30799146918
state at handoff creation: queued
```

The branch commits infrastructure and design notes only. Its disposable runner patch adds `INDEX_DESTRUCTURE`, emitted only for object and array matchers. The new operation indexes the binding value, skips the mismatched-root integrity check, records the matcher component, and preserves the original `value_at_path` passed through `as`.

First incomplete step: classify focused run `30799146702` first. If semantic cases pass, retain its patch, source hashes, disassembly, artifact digest, Valgrind output, full-suite result, and all ordinary workflow conclusions before deciding whether to commit product source.

## systemd bind-path whitespace overlap

```text
canonical issue: systemd/systemd#43214
active PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled product branch: none
```

Documentation review established the valid grammar:

```text
source[:destination[:rbind|norbind]]
```

When destination is omitted, options must also be omitted. `source::norbind` is a negative control.

Run `30759715925` verified both exact source heads but failed before compilation because the carrier invoked `meson setup systemd/build` from the checkout parent. Both jobs produced the same Meson source-directory error. No parser or serialization result was executed.

Retained artifacts:

```text
canonical base: 8838880432
  digest: sha256:65b940618c63baefaf6dde22a95febb2f47ce6cea5d6ddef82b0f90417864797
active PR: 8839366457
  digest: sha256:fba8903937e894d5356c0f88eb4a7551f2372f2e49f19d557d46c0ba2a331155
```

Commit `8a909171aac4944e27ae257af1fba6aaae21bdad` repaired only the invocation to `meson setup systemd/build systemd`. The detailed handoff is:

```text
investigations/systemd-bind-path-whitespace-overlap/HANDOFF.md
```

First incomplete step: resolve the first systemd comparison run on the final Linux Fieldwork head, classify build and every parser case, then run the narrowest source-native serialization/deserialization round-trip. Do not approve the active PR from `systemd-analyze verify` alone.

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

1. jq fork run `30799146702` and ordinary workflows.
2. final-head systemd base/PR comparison, followed by serialization round-trip.
3. UV clean parse-first exact-source experiment.
4. Continue discovery only after checking overlap; prefer one ownable source candidate over several duplicate reviews.

## Cleanup state

No local repository checkout survived because the runtime cannot resolve `github.com`. Hosted workflows own build products and temporary cleanup. Unused fork-local carrier-base branches contain no product source changes and are not referenced by any active PR. No credential, service, mount, device, or canonical upstream state was created.

## Publication boundary

All pull requests and workflows referenced here are internal or controlled-fork carriers. No canonical upstream communication has been authorized or made.
