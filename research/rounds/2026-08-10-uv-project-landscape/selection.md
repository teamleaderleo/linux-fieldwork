# UV project landscape — 2026-08-10

State: CURRENT-SNAPSHOT RESEARCH / SELECTION MAP

Fieldwork issue: #505

Current upstream snapshot used for this pass:

```text
1881d30773386da77017f2ad5ceaf160535d65da
```

External commit context:

- https://redirect.github.com/astral-sh/uv/commit/1881d30773386da77017f2ad5ceaf160535d65da

No canonical upstream interaction is authorized by this record.

## In simple words

UV is no longer just an unusually fast package installer. The active project surface now spans a resolver, lockfile/workspace model, pip-compatible requirements parser, build frontend/backend templates, tool runner, Python manager, cache/extraction system, cross-platform launcher/runtime machinery, and a release pipeline that is itself being optimized.

That makes the highest-value Fieldwork work less about finding isolated suspicious lines and more about checking contracts where two layers meet:

- a relative path in a file versus a path passed by the caller;
- an installed tool receipt versus a later ephemeral tool invocation;
- workspace discovery versus same-name group precedence;
- extracted archive identity versus shared payload lifetime;
- generated project-template semantics versus raw backend capability;
- portable launcher safety versus an implementation-specific utility parser.

The current Fieldwork runbook's intent/context and adjacent-context rules fit UV particularly well because many apparent bugs are really ownership or semantic-boundary questions.

## Current project direction

### 1. Resolver performance and diagnostics remain first-class product work

Recent mainline work continues to optimize dependency solving and error explanations, including widening unavailable-version ranges and preserving diagnostic context. This is mature core logic with substantial test coverage, so Fieldwork should avoid speculative solver rewrites and prefer small reproductions where the same requirement graph behaves differently across command surfaces or metadata representations.

Selection rule: only open a solver lane when the fixture can distinguish resolver logic from index data, metadata extraction, Python-range handling, or command-specific filtering.

### 2. Large-workspace semantics and performance are active

Workspaces now own more dependency-group behavior and are being optimized for large member sets. The same-name dependency-group report at https://redirect.github.com/astral-sh/uv/issues/20917 initially looked like a 0.12 regression, but maintainer intent evidence says the former root/member merging was incidental rather than a contract to restore. Fieldwork #506 was therefore retired without a product candidate.

Lesson: workspace behavior needs an intent check before regression framing. Root-versus-member context is often a semantic input, not merely a filesystem location.

### 3. Tool environments have a richer identity than the user-facing shorthand suggests

The live report at https://redirect.github.com/astral-sh/uv/issues/20981 exposes a useful contract boundary.

Current CLI/help documentation says an installed tool will be used by `uvx` / `uv tool run` unless a version is requested or `--isolated` is used. Current source, however, only reuses the installed environment when the current serialized `ToolOptions` equal the options stored in the install receipt. `exclude-newer` is one of those identity fields.

That means the implementation has a coherent concept — "reuse a compatible installed environment" — but the public promise currently reads more broadly than that compatibility relation. Fieldwork #508 remains live as a contract-drift investigation rather than being classified prematurely as a resolver bug.

Useful adjacent contexts:

- direct installed executable;
- `uv tool run`;
- `uvx` alias;
- explicit `@version`;
- `--isolated`;
- offline mode;
- same versus different resolver/index options.

Stop condition: either the docs/help are narrowed to the actual compatibility rule, or product intent explicitly chooses installed-version identity over receipt-option identity and a reproducible code change is warranted.

### 4. Requirements-file path identity is an active regression surface

The fresh report at https://redirect.github.com/astral-sh/uv/issues/21016 says relative `--find-links` entries fail on macOS x86_64 in 0.12.x despite the recently merged https://redirect.github.com/astral-sh/uv/pull/20832, which was intended to resolve requirements-file paths relative to the containing file.

Current source already joins an existing relative path to the requirements file's directory before converting it to a filesystem URL, so the report is not explained by missing parser logic.

Fieldwork #504 first ran a Linux cross-version matrix using a real local wheel. All 96 rows passed across 0.11.26, 0.12.0, 0.12.1, 0.12.2, 0.12.3, and pinned current main for both `pip compile` and `pip install --dry-run -r`, direct and nested requirements-file paths, several relative syntaxes, and absolute controls.

That negative result narrows the likely discriminator to the reporter's macOS x86_64 platform or another path-identity context that the plain Linux fixture does not exercise. A matching Intel-macOS carrier is now the next discriminator before mediated `-r` / `-c` inclusion is explored.

This is currently the strongest immediate Fieldwork bug lane because a recent fix, current source, and a fresh observed report disagree in a falsifiable way.

### 5. Cache/extraction is moving toward content-addressed identity

The preview stack around:

- https://redirect.github.com/astral-sh/uv/pull/19693
- https://redirect.github.com/astral-sh/uv/pull/19694
- https://redirect.github.com/astral-sh/uv/pull/20737

is architecturally important.

The first layer gives extracted wheel trees a deterministic directory digest that includes logical paths, sizes, executable bits, file contents, and explicit empty leaf directories while ignoring ZIP ordering and other non-semantic archive metadata. The next layer moves selected native payloads into separately content-addressed objects referenced by archive manifests so duplicate large binaries can be shared.

This changes the interesting correctness questions from "did extraction finish?" to lifecycle invariants such as:

- can an incomplete object become visible after interruption?
- can concurrent extraction publish two identities for the same logical tree?
- can prune/clean collect a manifest-backed payload while another archive still references it?
- do hardlink/copy fallback paths preserve executable-bit and conflict semantics?
- do streaming and seekable extraction compute the same logical identity under archive-order and metadata variation?

Fieldwork #510 tracks this as project-learning research. The stack is still open/preview-gated, so no product candidate should be created merely to anticipate races. Promote only when a concrete lifecycle invariant is missing from the upstream test inventory or an executable adjacent context can overturn a design claim.

### 6. Release performance is becoming product engineering

The profile-guided optimization work at https://redirect.github.com/astral-sh/uv/pull/21001 is a notable project-direction signal. It trains actual release binaries against checked-in real-project dependency graphs and evaluates on separate held-out projects rather than relying only on synthetic microbenchmarks.

The Linux x86-64 prototype reports meaningful resolver/export speedups and materially smaller release artifacts, at the cost of a substantially longer release build. Companion platform work exists for other release targets.

Fieldwork value here is not to duplicate benchmark numbers. A useful independent lane would need a concrete portability or representativeness discriminator — for example, a workload class that is systematically absent from training but materially regresses under the optimized binary, or a platform-specific release artifact whose linkage/CPU baseline changes. Without such a discriminator, treat this as current project context rather than a candidate bug.

### 7. Cross-platform launchers and runtime shims expose ownership boundaries

The Alpine/BusyBox report at https://redirect.github.com/astral-sh/uv/issues/16209 is a good negative example. BusyBox `realpath` complains about `--`, but removing `--` from UV's generated wrapper weakens protection for dash-prefixed operands on conforming implementations.

The BusyBox-side discussion at https://redirect.github.com/vda-linux/busybox_mirror/issues/26 agrees that `--` handling belongs centrally in BusyBox's applet dispatch rather than in a UV-specific `realpath` workaround.

Fieldwork #509 therefore closed as an ownership result. Lesson: cross-platform noise is not automatically owned by the project that exposes it. Preserve the stronger portable invariant unless the lower layer cannot carry the repair.

### 8. Generated backend templates are product semantics, not just backend selection

The completed simple-stub work remains a useful example beyond the specific bug. Raw backend capability and UV's selected project-template meaning are not always the same thing: scikit-build-core can package a pure stub wheel, while UV currently presents its Scikit template as an extension-module starter.

That distinction is why the current controlled candidate rejects the generated simple-stub Scikit combination while preserving `--bare`, even though a clean CMake-less Scikit fallback was independently proven.

General lesson: when investigating `uv init`, ask both "can this backend technically do it?" and "does this selector currently promise that project family?"

## Current selections

### Execute now

#### #504 — relative `--find-links` path identity

Why selected:

- fresh regression report;
- a recently merged fix claims the same invariant;
- current source appears to implement the intended rule;
- first Linux matrix is a high-confidence negative;
- reporter platform gives a clean next discriminator.

Next action: exact Intel macOS reproduction, then only if needed mediated requirements inclusion / constraints contexts.

#### #508 — installed-tool identity versus tool-run compatibility

Why selected:

- current implementation behavior is explainable from source;
- current user-facing help says something broader;
- maintainer discussion describes a narrower intended workflow than the CLI help;
- direct executable / tool-run / uvx / offline / option-delta contexts can distinguish documentation drift from product-semantics drift.

Next action: source-map the receipt compatibility fields and run a small deterministic identity matrix if the source/docs comparison alone cannot close the question.

### Reference / observe

#### #510 — content-addressed cache transition

Why not executable yet: preview stack is still moving and there is no concrete observed invariant failure. Keep a test-family map so Fieldwork can move quickly if an interruption, cleanup, deduplication, or link-mode failure appears.

#### PGO release series

Why not execute now: upstream work already contains a careful training/evaluation split and artifact checks. Independent value requires a missing workload/platform discriminator, not a second benchmark run.

### Retired after intent/ownership challenge

#### #506 — workspace same-name `dev` group behavior

Disposition: not a regression-fix target under current maintainer intent. Desired additive semantics are feature-design work.

#### #509 — BusyBox `realpath --`

Disposition: UV-side removal is the wrong owner because it weakens operand safety; BusyBox-side parsing is the cleaner repair boundary.

## Testing and evidence style learned from UV

A recurring project pattern is that permanent UV tests tend to own deterministic local contracts — parser behavior, generated files, snapshots, command semantics — while expensive third-party or platform matrices are better used as bounded evidence rather than automatically becoming permanent CI.

The simple-stub lane validated this split successfully: focused UV-native tests own generated template behavior; Fieldwork execution carriers supplied exact third-party artifact evidence.

For broader UV work, prefer the same separation:

- upstream/product tests should guard the project's deterministic contract;
- Fieldwork can use hosted cross-version/platform/backend matrices to prove a boundary before proposing permanent coverage;
- do not turn every research discriminator into long-lived networked CI.

## Existing stub candidate freshness

Controlled UV #82 remains design/artifact complete, but its comparison base is:

```text
dd0584d560a4693b5713a78be54304123ada3e77
```

Current upstream main for this landscape pass is one later unrelated commit:

```text
1881d30773386da77017f2ad5ceaf160535d65da
```

The intervening change is a lenient-requirement parser fix, not stub/init work. Treat this as an ordinary freshness/rebase check before any future upstream-facing use of #82, not as a reason to reopen the selected design.

## Selection discipline going forward

Before opening another UV lane, require at least one of:

1. a current observed failure with a small exact fixture;
2. a recent fix and a current report that disagree;
3. a cross-command/platform/representation context that can overturn the obvious explanation;
4. a lifecycle or authority boundary whose failure would corrupt durable state;
5. a documentation/CLI contract that disagrees with executable behavior in a decision-relevant way.

Do not select work merely because an issue is old, technically interesting, or easy to patch.

## Publication boundary

This is internal research. External GitHub references in Fieldwork interaction text use `https://redirect.github.com/...`.

No comments, reactions, reviews, pull requests, email, or other canonical upstream interaction are authorized or performed by this record.
