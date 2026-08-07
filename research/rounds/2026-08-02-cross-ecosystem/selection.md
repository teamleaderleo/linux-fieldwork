# Cross-ecosystem candidate round — 2026-08-02

## Goal

Move beyond the saturated mmdebstrap lane and identify concrete, bounded contribution work across unrelated repositories and ecosystems. A fork is an execution surface, not evidence by itself. Each promoted item needs a current defect or cleanup target, an exact source boundary, a distinguishing test or probe, and no active equivalent implementation unless the work is explicitly an overlap review.

External contact authorized: `false`.

## Current portfolio

### UV: recognize UV lockfiles passed through requirements-syntax file lanes

State: `HOLD — PRE-PARSE DESIGN HAS A REAL FALSE POSITIVE`.

```text
canonical issue: astral-sh/uv#16192
controlled fork: teamleaderleo/uv
source PR: #12
base: 1da26a68629be6ae5fd7f924a7d49ff54763a7df
source head: ba55497fe83ea9bb07c04452f8ba190fa4440a05
parse-first experiment PR: #13
experiment head: f0673123cbabe859c12fe6baacc1fff872060f17
```

The source correctly models UV's producer names through native path operations:

- exact project lock `uv.lock`;
- script lock `<complete-native-script-filename>.lock` when the exact sibling parses as PEP 723;
- non-UTF-8 Unix filenames remain representable;
- lockfile contents are not guessed.

Review found a stronger collision: detection occurs before requirements parsing. A valid requirements file named `action.py.lock` is rejected whenever neighboring `action.py` is valid PEP 723. Possible producer naming is weaker evidence than a successful requirements parse.

Execution results so far do not validate either source design:

- clean source carrier run `30754710006` reached rustfmt and failed only formatting, but that source is already semantically superseded by the collision;
- parse-first experiment run `30755038821` failed before compilation because its runner-local textual patch no longer matched the repaired source; its fallback formatting step also lacked the `rustfmt` component.

These are carrier results, not UV product failures. The next valid work is a clean parse-first source transformation against the exact current head, followed by formatting, affected-crate compilation, and focused producer-backed tests.

Workspace: `investigations/uv-lock-requirements-diagnostic/`.

### WGPU/Naga: `vec2<f16> ↔ u32` bitcast capability

State: `RETIRED — CURRENT NAGA ACCEPTS BOTH DIRECTIONS`.

```text
canonical issue: gfx-rs/wgpu#8896
controlled fork: teamleaderleo/wgpu
evidence head: b39e1822d3317e1b2ab41108211adf048314fa7d
focused run: 30752907389
focused job: 91509997426
artifact: 8835144866
artifact digest: sha256:b507a9437f6f67de315317c79f4301b830388afd0072d66fcc5431a5615c8778
```

The neutral capability matrix accepted:

```text
scalar f32 → u32
vec2<f16> → u32
u32 → vec2<f16>
```

All three returned status zero and `Validation successful`; all stderr files were empty. Ordinary WGPU workflows Shaders, Publish, Lazy, Docs, cargo-generate, CTS, and CI also passed.

The first red run belonged to a stale expected-failure classifier, not Naga. The internal fork PR was closed without merge after the exact receipt and handoff were retained.

Workspace: `investigations/wgpu-naga-f16-bitcast/`.

### jq: destructuring path context

State: `ACTIVE — FOUR-VARIANT SOURCE MATRIX QUEUED`.

```text
canonical issue: jqlang/jq#3128
canonical source: 603db3f57741d217ba651e61086b550a72148b83
src/compile.c blob: 80b723c119b45f99c5e847c2a463568eb730f498
closed prior attempt: jqlang/jq#3384
open equivalent PR: none found
controlled workflow run: 30759608059
```

The minimal issue is not a one-line fix. Closed PR #3384 removed the error but still produced incorrect paths and was abandoned after stack/path interactions surfaced.

The controlled matrix compares:

1. current baseline;
2. the closed PR's source logic;
3. the issue draft with `SUBEXP_END` before `POP`;
4. the unresolved inverse order, `POP` before `SUBEXP_END`.

Every row builds exact jq source, runs seventeen object/array/alternation/backtracking controls, retains bytecode disassembly, executes Valgrind discriminators, and runs complete `make check`.

The first workflow definition failed to register because top-level concurrency referenced the job matrix. That carrier bug was fixed at `32570b31838f9f9d8a494e435a43b5f59de7cde6`; run `30759608059` is the first valid named matrix. No jq product result is claimed yet.

Workspace: `investigations/jq-destructure-path-context/`.

### systemd: repeated whitespace in bind-path directives

State: `ACTIVE OVERLAP REVIEW — BASE/PR SOURCE COMPARISON QUEUED`.

```text
canonical issue: systemd/systemd#43214
active PR: systemd/systemd#43217
canonical base: 63e35ca3f99566095c84248e9eb41a3a6b32f2eb
active PR head: d32993d1f67ec1b42719c89eeda9425042df57ce
controlled workflow run: 30759608071
```

Debian 13 systemd 257 reproduced empty-path warnings from repeated spaces and continuation indentation.

Documentation review corrected an earlier Fieldwork assumption. The documented grammar is:

```text
source[:destination[:rbind|norbind]]
```

and options must be omitted when destination is omitted. `source::norbind` is invalid, not compatibility syntax.

The corrected fixture now separates documented valid tuples, repeated/mixed whitespace, quoting, escaped colons, markers and reset behavior from documented invalid omitted-destination, extra-field and invalid-option controls.

Run `30759608071` builds `systemd-analyze` from both canonical base and exact active PR head, then retains every parser result. Serialization/deserialization remains a separate required gate because the PR changes those paths too.

Workspace: `investigations/systemd-bind-path-whitespace-overlap/`.

## Screened overlap and negative results

### OpenTelemetry JS #6967

Current and high-value, but canonical PR #6969 already owns a broader fix: non-string host candidates, cross-realm URL classification, method/path guards, and a safety wrapper around attribute computation. Review target only.

### ripgrep #3222

Real dash-leading compressed-filename bug, but canonical PR #3224 and a duplicate already exist. No new patch.

### sharkdp/bat

Recent obvious defects already have active fixes:

- log-syntax catastrophic performance #3866 → PR #3876;
- huge line-range panic #3845 → multiple active PRs;
- width-one wide-character panic #3844 → active PRs;
- cache help exit behavior #3798 → active PRs.

No competing patch selected.

### sharkdp/fd

Recent candidates also have current owners:

- native-Windows glob separator bug #2067 → PR #2074;
- date parsing/message issue #2053 → PR #2088.

No competing patch selected.

### Workerd #176

The 2022 cache request is obsolete: current workflow already uses GitHub cache, Cloudflare remote Bazel cache, bounded content-derived keys, and trimming.

### Execa

Search surfaced stale closed bugs. The async iterator documentation request is not portable across the supported Node range.

### UV file-lock `EINTR`

Issue #15996 is valid, but active PR #19388 already covers the lock paths and Android.

### libarchive

Controlled non-seekable 7-Zip evidence is complete and active canonical PR #3070 remains open.

## Decision

Continue broad discovery, but promotion remains strict. The round now has:

1. one UV source idea held after a real false-positive discovery;
2. one WGPU issue retired with exact successful negative evidence;
3. one unclaimed jq compiler investigation with a distinguishing four-layout matrix;
4. one systemd overlap review with corrected documented grammar and source comparison;
5. multiple overlap/stale findings that prevented duplicate work.

No canonical upstream issue, pull request, comment, review, email, or patch submission was created.
