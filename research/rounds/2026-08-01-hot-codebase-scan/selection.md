# Hot codebase contribution scan — selection record

Date: 2026-08-01  
Branch: `research/hot-codebase-scan-20260801`  
Programme: [`ecosystem-contributions`](../../../programmes/ecosystem-contributions/STATUS.md)  
External contact authorized: `false`

## Purpose

This is a bounded portfolio scan requested after the mmdebstrap fork was created. It identifies current high-leverage codebases and concrete contribution surfaces without opening speculative implementation lanes or contacting upstream.

The selection rule is the Linux Fieldwork promotion rule: exact source identity, a repeatable command or fixture, meaningful consequence, likely owning files, current overlap review, and the smallest credible next change.

## Fork inventory confirmed

The authenticated account currently has controlled forks for several strong targets, including:

- `teamleaderleo/mmdebstrap` — default branch `master`;
- `teamleaderleo/buildkit`;
- `teamleaderleo/codex`;
- `teamleaderleo/workerd`;
- `teamleaderleo/uv`;
- `teamleaderleo/systemd`;
- `teamleaderleo/libarchive`;
- `teamleaderleo/util-linux`;
- `teamleaderleo/wgpu`;
- `teamleaderleo/deno`;
- `teamleaderleo/vite`;
- `teamleaderleo/playwright`.

A fork is execution capacity, not evidence that a lane is ready. Each candidate below still requires a fresh fork sync and exact-head baseline before source changes.

## Ranked current candidates

### 1. Codex configuration precedence can widen filesystem access

Upstream issue: `openai/codex#36448`  
Issue state during scan: open, unassigned, zero comments  
Active equivalent PR found: none  
Current upstream head observed: `ee0247f95a6fe2b094ba2253d82cae2a2b4c2dff`  
Reported release: `codex-cli 0.146.0`

#### Consequence

When both legacy `sandbox_mode` and beta `default_permissions` are present, observed behavior gives `default_permissions` precedence even though the published rule says `sandbox_mode` wins. The concerning direction is reproducible with `sandbox_mode = "read-only"` and `default_permissions = ":workspace"`: a write succeeds despite the explicit read-only setting.

#### Why this ranks first

- deterministic, throwaway `CODEX_HOME` reproduction;
- no privileged host, external service, or large fixture required;
- permission widening is materially more important than a cosmetic config mismatch;
- current issue has no assignee, comments, or active PR;
- likely source and test ownership are already narrow.

#### Likely owning surfaces

- `codex-rs/core/src/config/mod.rs`;
- `codex-rs/core/src/config/config_loader_tests.rs`;
- `codex-rs/config/src/config_toml.rs`;
- permission-profile compilation and compatibility resolution under `codex-rs/core/src/config/`.

#### First bounded probe

1. Sync `teamleaderleo/codex` to exact upstream head.
2. Reproduce both precedence directions with disposable `CODEX_HOME` and disposable working directories.
3. Locate the exact selection point where `default_permissions` and `sandbox_mode` converge.
4. Add a table-driven config-loader test covering both directions, CLI override, and profile selection.
5. Decide only from repository tests and current documentation whether code or docs own the correction; do not assume the issue report's desired precedence before tracing source intent.

Promotion gate: one failing baseline test that becomes a stable policy test, plus complete overlap review immediately before branch creation.

### 2. BuildKit drops generated proxy environment from later gateway processes

Upstream issue: `moby/buildkit#6994`  
Issue state during scan: open, unassigned, `kind/bug`, `status/triage`, `area/frontend`, `area/executor`, zero comments  
Active equivalent PR found: none  
Issue reproduction commit: `f5d08d5a04381687203ced27ef877e0c417fd122`  
Current upstream head observed: `275d6864ff0ce91a06225af5f5b012887bd257cf`  
Current controlled-fork head observed: `df0761886a20e368d75e0aa6bb3f20874f58b692`

#### Consequence

A gateway container created with `SolveOpt.ProxyNetwork` receives generated `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` variables in its initial process, while a later process launched through `Container.Start` loses them. User-supplied `StartRequest.Env` entries survive, so the defect is specific to BuildKit-owned proxy environment propagation.

#### Why this ranks second

- complete Go reproducer is already present in the issue;
- the initial-process/later-process differential sharply identifies the ownership boundary;
- proxy-dependent build frontends can fail only after the first process, producing confusing environment-dependent behavior;
- no equivalent PR or claim was found;
- the fix is likely reviewable as one gateway/executor environment composition change plus integration regression.

#### Capability cost

The exact reproducer builds BuildKit, starts a privileged BuildKit container, pulls BusyBox, and runs the gateway client. This is practical in a disposable Docker host but heavier than the Codex probe.

#### First bounded probe

1. Sync `teamleaderleo/buildkit` to the exact current upstream head.
2. Run the issue's reproducer unchanged and retain initial/exec environment sections.
3. Trace where `ProxyNetwork` creates the generated proxy environment and where subsequent `StartRequest.Env` is composed.
4. Add an integration case asserting generated proxy variables plus caller variables on both initial and later processes.
5. Verify caller-provided proxy variables retain documented precedence rather than being silently overwritten.

Promotion gate: baseline failure on exact current head, source-level ownership trace, and clean immediate rerun after container cleanup.

### 3. uv serializes a transitive Poetry editable source as an absolute path

Upstream issue: `astral-sh/uv#20477`  
Issue state during scan: open, `bug`, unassigned  
Active equivalent PR found: none  
Current upstream head observed: `79bbface771210df216b738e9bdc7df95e5a9e6b`

#### Consequence

A uv project with a direct editable path dependency can write that source as an absolute path in `uv.lock` when a transitive Poetry project also declares the dependency as editable. The same minimal direct-source shape stays relative. The lockfile therefore becomes machine-specific only when source information is merged across the transitive Poetry boundary.

#### Why this is secondary

- maintainer acknowledged the refined case as a bug after the initial report was narrowed;
- the reporter supplied a deterministic Dockerfile and a known-good older release;
- no active PR was found;
- impact is real for monorepos and per-package lockfiles, but narrower than the first two candidates.

#### First bounded probe

1. Run the refined Dockerfile against current release and current source.
2. Reduce the Poetry metadata to the smallest field set that changes source identity.
3. Trace source normalization/merging introduced around the reported 0.10.10 boundary.
4. Add a lock snapshot test requiring relative identity for a direct source shared with a transitive Poetry editable dependency.
5. Verify Windows path and workspace behavior before selecting a serialization fix.

Promotion gate: current-head reproduction and a reduced fixture that distinguishes ordinary direct paths from the transitive Poetry case.

## High-value deep lane, currently held

### workerd Hyperdrive Worker-designator process crash

Upstream issue: `cloudflare/workerd#6901`  
Current upstream head observed: `d82c2a45a8695aac30d4d24828ce1ee7fb11909b`  
Active PR found: none

A local Cap'n Proto configuration can direct a Hyperdrive binding at another Worker service; accepting that synthetic connection returns success and then crashes the workerd process with SIGSEGV during deferred teardown. This is a serious runtime hardening surface with a self-contained reproduction.

Hold reason: the reporter has already performed the lifetime analysis, drafted a defensive guard, and explicitly offered to prepare the PR after maintainers choose config-time failure versus JS-catchable runtime failure. Independent implementation now risks duplicating active design work. Retain this as a review/test opportunity if maintainers request validation or the reporter abandons the lane.

## Active-fix and policy stops

### workerd Buffer `*Write` omitted length

Issue `cloudflare/workerd#6875` is a clear ecosystem-breaking bug, but active PR `cloudflare/workerd#6891` already changes all seven methods and adds regression coverage. Do not create a competing implementation. A useful role would be independent review against Node semantics if requested.

### uv index override propagation

Issue `astral-sh/uv#20765` is currently explained by documented intentional behavior: named indexes referenced by `tool.uv.sources` must be declared in the project and are not supplied by command-line, environment, or user-level configuration. Do not promote it as a source defect without a policy change from maintainers.

## Current decision

The strongest immediate technical probe is Codex issue #36448 because it combines deterministic local execution, narrow source ownership, no capability gate, and a potentially unsafe permission-widening result.

BuildKit issue #6994 is the strongest Linux/container lane and should be next when a disposable privileged Docker host is available.

uv issue #20477 remains a good smaller Rust regression after the two higher-consequence boundaries are classified.

Do not begin workerd #6901 implementation while the reporter's design offer remains live. Do not duplicate workerd PR #6891 or treat uv #20765 as a defect.

## External-contact state

The scan read public repository, issue, pull-request, and commit state only. No upstream issue, pull request, comment, review, email, or other public contact was made.
