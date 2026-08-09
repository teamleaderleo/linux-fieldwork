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

Recent mainline work continues to optimize dependency solving and error explanations, including widening unavailable-version ranges, reusing workspace exclusion matchers, streaming workspace metadata output, and preserving diagnostic context while shrinking conflict search. This is mature core logic with substantial test coverage, so Fieldwork should avoid speculative solver rewrites and prefer small reproductions where the same requirement graph behaves differently across command surfaces or metadata representations.

Selection rule: only open a solver lane when the fixture can distinguish resolver logic from index data, metadata extraction, Python-range handling, workspace filtering, or command-specific behavior.

### 2. Large-workspace semantics and performance are active

Workspaces now own more dependency-group behavior and are being optimized for large member sets. The same-name dependency-group report at https://redirect.github.com/astral-sh/uv/issues/20917 initially looked like a 0.12 regression, but maintainer intent evidence says the former root/member merging was incidental rather than a contract to restore. Fieldwork #506 was therefore retired without a product candidate.

Lesson: workspace behavior needs an intent check before regression framing. Root-versus-member context is often a semantic input, not merely a filesystem location.

### 3. Installed tool version and installed environment identity are different concepts

The report at https://redirect.github.com/astral-sh/uv/issues/20981 exposed a contract boundary that Fieldwork #508 has now executed to completion.

Current CLI/help and concepts documentation say that once a tool is installed with `uv tool install`, `uvx` / `uv tool run` will use the installed version by default unless a version is requested or `--isolated` is used. Current source, however, only reuses the persistent installed environment when the current serialized `ToolOptions` equal the options stored in the install receipt; `exclude-newer`, index settings, find-links, and other resolver settings are part of that identity.

Fieldwork #508 used a deterministic local `probe-tool==1.0.0` wheel that prints its own `sys.prefix`, so package-version selection and environment reuse could be separated. Receipt: run `31342055932`, job `93317345829`, artifact `uv-tool-identity-508` ID `9046169127`, SHA-256 `b7dee8e1eebbad9b1042f8995cba4acb5e0e11080b3bf1814d91b3215f7788f7`.

Observed identically on released 0.12.3 and current main:

- matching install-time options reuse the persistent installed environment;
- omitting only `--exclude-newer` uses an ephemeral cache environment even though the only selectable package remains exactly `probe-tool==1.0.0`;
- `--isolated` uses the ephemeral environment;
- explicit `probe-tool@1.0.0` with matching options reuses the installed environment;
- the released `uvx` alias follows the same matching/mismatching behavior.

Maintainer guidance on the canonical issue says direct invocation is the intended pattern after `uv tool install` and `tool run` is mostly intended for ephemeral tools. The first mismatch is therefore the user-facing help/docs contract, not resolver correctness.

Lowest-risk first direction: describe reuse as conditional on the installed environment being compatible with current tool options. Keep any redesign of exact `ToolOptions` equality separate. In particular, some fields such as `exclude-newer` may have directional compatibility semantics while index provenance may need stricter identity; that is product design, not required to correct the current public promise.

Fieldwork #508 and its execution carrier are closed completed.

### 4. Requirements-file path identity remains the strongest live bug discriminator

The report at https://redirect.github.com/astral-sh/uv/issues/21016 says relative `--find-links` entries fail on macOS x86_64 in 0.12.x. A related but distinct containing-file bug was fixed by https://redirect.github.com/astral-sh/uv/pull/20832.

Current source already joins an existing relative path to the requirements file's directory before converting it to a filesystem URL, so the public report is not explained by simply missing that parser logic.

Fieldwork #504 now has two Linux results with a corrected evidence boundary.

#### Direct/root-file Linux control

A real local-wheel matrix showed the public report's direct/root-file shape does **not** reproduce on Linux: 0.11.26, 0.12.0, 0.12.1, 0.12.2, 0.12.3, and current main all succeeded for the direct requirements-file cases under both `pip compile` and `pip install --dry-run -r`, with relative and absolute controls.

The first version of this matrix also had nested rows, but those were invalid as containing-file evidence because it created a same-named wheel directory at both the command cwd and nested requirements directory. That masking fixture was explicitly corrected in the Fieldwork record rather than retained as proof.

#### Corrected containing-file Linux discriminator

The corrected fixture matches the ownership distinction in https://redirect.github.com/astral-sh/uv/pull/20832: command cwd has no `links/`; only `requirements/links/` exists beside the nested requirements file.

Receipt: run `31342108978`, job `93317482600`, artifact `uv-find-links-504-nested` ID `9046187836`, SHA-256 `fc7a4c2408a51b04da9e745601e5135a6d71874a4bfb9bfbce6248571e85eb81`.

Release boundary for both whitespace/equal forms and both compile/install commands:

- 0.11.26: 0/4 pass — `relative URL without a base`;
- 0.12.0: 0/4 pass — same failure;
- 0.12.1: 4/4 pass;
- 0.12.2: 4/4 pass;
- 0.12.3: 4/4 pass;
- current main: 4/4 pass.

This confirms the containing-file-relative behavior was repaired from 0.12.1 onward on Linux. It also separates that bug from the public direct/root-file macOS report.

macOS x86_64 is a UV Tier 1 platform, so a platform-only reproduction would still be product-significant. An exact Intel-macOS carrier is queued as the next discriminator. If it reproduces while Linux direct/root controls stay green, first-owner classification should move toward platform-specific path existence/absolute/file-URL handling rather than generic `requirements_dir` parsing.

Do not explore mediated `-r` / `-c` inclusion until the direct macOS discriminator is known.

### 5. Cache/extraction is moving toward content-addressed identity

The preview stack around:

- https://redirect.github.com/astral-sh/uv/pull/19693
- https://redirect.github.com/astral-sh/uv/pull/19694
- https://redirect.github.com/astral-sh/uv/pull/20737

is architecturally important.

The first layer gives extracted wheel trees a deterministic directory digest that includes logical paths, sizes, executable bits, file contents, and explicit empty leaf directories while ignoring ZIP ordering and other non-semantic archive metadata. The next layer moves selected native payloads into separately content-addressed objects referenced by archive manifests so duplicate large binaries can be shared.

The public cache contract matters more than internal object/bucket names. Current UV documentation describes the cache as thread-safe and append-only, robust to concurrent readers/writers, and expects forwards/backwards compatibility for changes that remain within one cache-bucket version.

That sharpens useful lifecycle invariants:

- incomplete objects/manifests must not become observably published;
- concurrent extraction must preserve one logical identity rather than race into conflicting visible state;
- prune/clean must not collect a payload still referenced by another archive manifest;
- hardlink/copy fallback must preserve executable-bit and conflict semantics;
- streaming and seekable extraction must compute the same logical identity under archive-order and metadata variation;
- representation changes within a shared bucket version must preserve cross-version reader/writer compatibility.

Fieldwork #510 tracks this as project-learning research. The stack is still open/preview-gated and no concrete failure currently justifies a product candidate.

### 6. Release performance is becoming product engineering

The profile-guided optimization work at https://redirect.github.com/astral-sh/uv/pull/21001 is a notable project-direction signal. It trains actual release binaries against checked-in real-project dependency graphs and evaluates on separate held-out projects rather than relying only on synthetic microbenchmarks.

The Linux x86-64 prototype reports meaningful resolver/export speedups and materially smaller release artifacts, at the cost of a substantially longer release build. Companion platform work exists for other release targets.

Fieldwork value here is not to duplicate benchmark numbers. A useful independent lane would need a concrete portability or representativeness discriminator — for example, a workload class systematically absent from training but materially regressed by the optimized binary, or a platform-specific release artifact whose linkage/CPU baseline changes. Without such a discriminator, keep this as project context.

### 7. Cross-platform launchers and runtime shims expose ownership boundaries

The Alpine/BusyBox report at https://redirect.github.com/astral-sh/uv/issues/16209 is a useful negative example. BusyBox `realpath` complains about `--`, but removing `--` from UV's generated wrapper weakens protection for dash-prefixed operands on conforming implementations.

The BusyBox-side discussion at https://redirect.github.com/vda-linux/busybox_mirror/issues/26 agrees that `--` handling belongs centrally in BusyBox's applet dispatch rather than in a UV-specific `realpath` workaround.

Fieldwork #509 therefore closed as an ownership result. Lesson: cross-platform noise is not automatically owned by the project that exposes it. Preserve the stronger portable invariant unless the lower layer cannot carry the repair.

### 8. Generated backend templates are product semantics, not just backend selection

The completed simple-stub work remains a useful example beyond the specific bug. Raw backend capability and UV's selected project-template meaning are not always the same thing: scikit-build-core can package a pure stub wheel, while UV currently presents its Scikit template as an extension-module starter.

That distinction is why the current controlled candidate rejects the generated simple-stub Scikit combination while preserving `--bare`, even though a clean CMake-less Scikit fallback was independently proven.

General lesson: when investigating `uv init`, ask both "can this backend technically do it?" and "does this selector currently promise that project family?"

## Current selections

### Execute now

#### #504 — relative `--find-links` path identity

Why still selected:

- fresh Tier-1-platform regression report;
- direct/root case is green on Linux across the claimed bad releases;
- corrected nested Linux matrix independently verifies the #20832 fix boundary at 0.12.1;
- current source appears to implement containing-file path resolution;
- reporter platform gives a clean next discriminator.

Next action: exact Intel-macOS direct/root reproduction. Only after that, if needed, inspect mediated requirements inclusion or platform-specific URL/path conversion.

### Completed contract research

#### #508 — installed-tool identity versus tool-run compatibility

Disposition: execution complete. Current implementation consistently treats the persistent installed environment as reusable only when receipt options are compatible. Public help/docs say something broader. First owner is documentation/help contract; future directional compatibility design is separate.

### Reference / observe

#### #510 — content-addressed cache transition

Why not executable yet: preview stack is still moving and there is no concrete observed invariant failure. The retained test-family map now anchors to the public thread-safe/append-only/cross-version cache guarantees rather than internal filenames.

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

The #504 fixture correction adds another methodological lesson: an adjacent-context fixture must not accidentally make both the intended and wrong ownership rules succeed. For relative-path tests, avoid same-named target directories at both candidate base locations.

For broader UV work, prefer the same separation:

- upstream/product tests should guard the project's deterministic contract;
- Fieldwork can use hosted cross-version/platform/backend matrices to prove a boundary before proposing permanent coverage;
- check fixture aliasing before interpreting path-identity results;
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
