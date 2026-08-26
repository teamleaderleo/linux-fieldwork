# Linux Fieldwork

A GitHub-hosted workbench for investigating Linux and Debian projects from a phone-first workflow.

> **Current work:** use live GitHub issues and pull requests together with programme/target state and the owning evidence records. [`CURRENT_FIELDWORK.md`](CURRENT_FIELDWORK.md) is a retired historical board, not a live-status authority.

## In simple words

Linux Fieldwork is a lab notebook and working copy for learning how Linux systems behave, mapping formal research directions, testing concrete questions, and preparing candidate fixes. Casual lessons belong in `notes/`. Formal possibilities live in `programmes/` and `research/`. Recurring upstream systems live in `targets/`. Repeatable technical claims belong in `investigations/`. Imported project trees live in `upstream/` with their source identity preserved.

## Enter here

- [`START_HERE.md`](START_HERE.md) — choose the right kind of work and record it consistently.
- [`WRITING.md`](WRITING.md) — make the question, consequence, evidence, limit, and decision readable without turning every record into the same template.
- [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md) — lightweight ownership, dispatch, review, branching, and quiet external-reference guidance.
- [`FIELD_GUIDE.md`](FIELD_GUIDE.md) — practical do, do-not, 🍩 donut, review, and investigation-selection lessons.
- [`RESEARCH_LANES.md`](RESEARCH_LANES.md) — current shortlist of formally mapped lanes.
- [`programmes/`](programmes/) — long-lived Linux research directions, lane registry, and formal lane directories.
- [`targets/`](targets/) — recurring upstream projects and subsystem maps.
- [`research/`](research/) — dated landscape rounds, selection records, and source orientation.
- [`notes/`](notes/) — Linux lessons, command discoveries, explanations, and small demonstrations.
- [`investigations/`](investigations/) — bounded questions with exact sources, commands, evidence, and limits.
- [`templates/`](templates/) — starter documents for notes and investigations.
- [`upstream/`](upstream/) — imported source trees used for reading, testing, and candidate patches.
- [`CURRENT_FIELDWORK.md`](CURRENT_FIELDWORK.md) — retired August 10 status-board surface retained only as a Git-history pointer.

## Working surfaces

**Programmes organize formal research.** Their registry preserves all plausible lanes. Programme status files carry current direction. Strong lanes receive dedicated directories with bounded questions, first probes, promotion signals, and stop signals.

**Targets orient recurring upstream systems.** A target map connects exact source identity, relevant programmes, mapped lanes, existing investigations, and contribution boundaries.

**Research rounds survey broad territory.** They retain selection reasoning and source orientation after their lane inventory has moved into programmes and targets.

**Notes capture reusable understanding.** Use them for concepts, commands, operational recipes, source-reading lessons, and behavior that can be demonstrated without a full research record.

**Investigations test bounded questions.** They record source revisions, environments, baseline behavior, hypotheses or candidate changes, reproduction commands, results, interpretation, evidence boundaries, and next steps.

**Imported source trees support real code work.** They provide preserved upstream revisions for reading, testing, and candidate changes.

A research round can add an inbox lane. A lane can receive a formal directory when its first probe is clear. A lane becomes an investigation when exact source work begins. General lessons can move into notes at any stage.

## Working source trees

Imported upstream projects live under `upstream/`. Their original files, licensing information, and executable permissions are preserved. Import metadata records the upstream repository, requested revision, resolved commit, and import time.

## Evidence discipline

Chat narration, tool output, and local memory are transient. The repository must carry enough current state for another worker to resume from exact commits, artifacts, and records without the conversation.

Durable technical claims should record:

1. the exact source revision or retrieval boundary;
2. the relevant environment, privileges, distribution, kernel, shell, and tool versions;
3. commands or steps another person can repeat;
4. baseline and candidate behavior when a change is involved;
5. observed results separated from interpretation;
6. the limits of the evidence;
7. whether any upstream contact has been authorized or made.

Negative results belong here too. A careful result that supports existing behavior can save future work.

## Repository map

- [`START_HERE.md`](START_HERE.md) — primary navigation and work-entry guide.
- [`CURRENT_FIELDWORK.md`](CURRENT_FIELDWORK.md) — retired historical board; do not use as current status.
- [`WRITING.md`](WRITING.md) — reader-facing technical-writing guidance.
- [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md) — adaptable coordination and third-party GitHub backlink policy.
- [`FIELD_GUIDE.md`](FIELD_GUIDE.md) — reusable review heuristics, common donuts, fruitful areas, and investigation-selection guidance.
- [`programmes/registry.yml`](programmes/registry.yml) — canonical programme and lane inventory.
- [`programmes/`](programmes/) — programme status files and formal lane directories.
- [`targets/registry.yml`](targets/registry.yml) — recurring target inventory.
- [`targets/`](targets/) — durable target maps.
- [`RESEARCH_LANES.md`](RESEARCH_LANES.md) — current mapped-lane shortlist.
- [`research/rounds/`](research/rounds/) — dated landscape rounds.
- [`notes/shell/`](notes/shell/) — shells, quoting, pipelines, scripts, and command behavior.
- [`notes/filesystems/`](notes/filesystems/) — paths, mounts, permissions, storage, and filesystem behavior.
- [`notes/packaging/`](notes/packaging/) — package formats, build systems, repositories, and package tooling.
- [`notes/processes/`](notes/processes/) — processes, signals, jobs, services, namespaces, and lifecycle behavior.
- [`notes/permissions/`](notes/permissions/) — users, groups, capabilities, privilege boundaries, and access control.
- [`notes/debian/`](notes/debian/) — Debian-specific policy, tooling, packaging, and project workflows.
- [`investigations/`](investigations/) — reproducible investigations and retained results.
- [`templates/`](templates/) — reusable starting points.
- [`upstream/`](upstream/) — preserved imported projects.

## Upstream boundary

This repository is separate from upstream Linux and Debian projects. Research, local patches, and candidate changes remain local until a deliberate decision authorizes an issue, email, merge request, patch submission, comment, or other upstream interaction.
