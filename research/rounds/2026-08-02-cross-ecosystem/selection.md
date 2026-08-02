# Cross-ecosystem candidate round — 2026-08-02

## Goal

Move beyond the saturated mmdebstrap lane and identify concrete, bounded contribution work across unrelated repositories and ecosystems. A fork is an execution surface, not evidence by itself. Each promoted item needs a current defect or cleanup target, an exact source boundary, a distinguishing test or probe, and no active equivalent implementation unless the work is explicitly an overlap review.

External contact authorized: `false`.

## Promoted investigations

### UV: recognize UV lockfiles passed through `-r`

- Canonical issue: `astral-sh/uv#16192`.
- Controlled fork: `teamleaderleo/uv`.
- Candidate branch: `fieldwork/uv-lock-requirements-diagnostic`.
- Candidate head: `a67f97bec7782c6f60aceefb2a9bcd7045582015`.
- Internal draft PR: `teamleaderleo/uv#12`.
- Exact base: `1da26a68629be6ae5fd7f924a7d49ff54763a7df`.
- Current canonical head checked: `79bbface771210df216b738e9bdc7df95e5a9e6b`.
- Canonical and controlled-base `crates/uv-requirements/src/sources.rs` blob: `cf6218326b96db5ce40e1fae31a0803e2c65e437`.
- CI run: `30752526287`, queued at the stopping point.

Selected design:

- recognize an existing file named exactly `uv.lock`;
- recognize `<script-name>.lock` only when the sibling script parses through UV's existing PEP 723 parser;
- retain arbitrary `.lock` files as requirements inputs;
- do not inspect or guess lockfile contents.

The previous upstream attempt `astral-sh/uv#16282` guessed from TOML substrings and was rejected. The controlled candidate uses filenames UV itself generates and a canonical sibling-script parser instead.

Workspace: `investigations/uv-lock-requirements-diagnostic/`.

### WGPU/Naga: current `vec2<f16> ↔ u32` bitcast capability

- Canonical issue: `gfx-rs/wgpu#8896`.
- Controlled fork: `teamleaderleo/wgpu`.
- Evidence branch: `fieldwork/naga-f16-bitcast-probe`.
- Current evidence head: `b39e1822d3317e1b2ab41108211adf048314fa7d`.
- Internal draft PR: `teamleaderleo/wgpu#4`.
- Exact base: `2eddc8c7b2fedd4267f5004745a8bc42974e17a0`.
- Current focused run: `30752907389`, queued at the stopping point.

The first run, `30752645663`, disproved the stale baseline assumption: current Naga accepted both the scalar control and the originally reported `vec2<f16> → u32` direction. The job failed only because the probe expected the old `Unable to cast` result and stopped before the reverse direction. Artifact `8834957333`, digest `sha256:aa8fb7e33a743b70026e709f8ed2167ba20351eba0ee1035435e73fe6d6c8da9`, retained the exact statuses and outputs.

The repaired probe is a neutral three-case capability matrix. The investigation will become either a stale-issue closeout or a narrowly restated reverse-direction defect.

Workspace: `investigations/wgpu-naga-f16-bitcast/`.

### systemd: repeated whitespace in bind-path directives

- Canonical issue: `systemd/systemd#43214`.
- Active equivalent implementation: `systemd/systemd#43217`.
- Active PR head checked: `d32993d1f67ec1b42719c89eeda9425042df57ce`.
- Controlled fork: `teamleaderleo/systemd`.
- Controlled source work: none.

Debian 13's installed systemd 257 reproduced empty-path warnings when `BindPaths=` or `BindReadOnlyPaths=` contained repeated inter-entry spaces or line-continuation indentation. The parser must preserve empty colon fields for `source::options`, but should not interpret repeated whitespace between entries as empty paths.

The active upstream PR rewrites more than the minimal whitespace boundary: parser representation, execution-context serialization/deserialization, and tests. This lane is retained as an overlap review rather than a competing source patch. Useful follow-up is to run distinguishing compatibility controls against the active PR.

Workspace: `investigations/systemd-bind-path-whitespace-overlap/`.

## Screened but not promoted to source work

### OpenTelemetry JS issue #6967

The HTTP instrumentation crash is current and high-value, but canonical PR `open-telemetry/opentelemetry-js#6969` already owns the fix. Its scope includes non-string host candidates, cross-realm URL classification, non-string method/path handling, and a safety wrapper around attribute computation. Retain as a review target; do not duplicate the implementation.

### ripgrep issue #3222

The dash-leading compressed-filename bug is real, but active PR `BurntSushi/ripgrep#3224` already adds per-tool `--` boundaries and discusses the compatibility tradeoff with path prefixing. A later duplicate PR also exists. Retain as overlap, not a new patch.

### Workerd issue #176

The 2022 request to cache GitHub Actions setup is obsolete against current `teamleaderleo/workerd`: `.github/workflows/_bazel.yml` already uses GitHub's cache action, Cloudflare's remote Bazel cache, bounded content-derived keys, and cache trimming. Retain as a stale-ticket cleanup observation; no code patch.

### Execa

The apparent open option-interaction bugs were stale search results and are closed on current upstream. The iterator-helper documentation request depends on JavaScript async iterator helper availability that is not present across Execa's supported Node range. No current patch selected.

### UV file-lock `EINTR`

Canonical issue `astral-sh/uv#15996` is valid, but active PR `astral-sh/uv#19388` already covers the lock paths and Android. Retain as overlap, not a duplicate implementation.

### libarchive

The controlled non-seekable 7-Zip evidence is already complete and active upstream PR `libarchive/libarchive#3070` remains open. No competing implementation.

## Decision

Continue broad discovery, but keep promotion strict. This round produced:

1. one small owned source candidate in UV;
2. one executable WGPU capability investigation already yielding a stale-issue signal;
3. one systemd overlap review with a durable reproducer;
4. current overlap or stale-ticket findings in OpenTelemetry, ripgrep, Workerd, Execa, UV locking, and libarchive.

No canonical upstream issue, pull request, comment, review, email, or patch submission was created.
