# Linux Fieldwork

A GitHub-hosted workbench for investigating Linux and Debian projects from a phone-first workflow.

## In simple words

Linux Fieldwork is a lab notebook and working copy for learning how Linux systems behave, testing concrete questions, and preparing candidate fixes. Short lessons belong in `notes/`. Reproducible technical claims belong in `investigations/`. Broad surveys and possible directions belong in `research/`. Imported project trees live in `upstream/` with their source identity preserved.

## Enter here

- [`START_HERE.md`](START_HERE.md) — choose the right kind of work and record it consistently.
- [`RESEARCH_LANES.md`](RESEARCH_LANES.md) — current shortlist of promising Linux and Debian investigation lanes.
- [`research/`](research/) — broad landscape rounds, source orientation, and first-probe designs.
- [`notes/`](notes/) — Linux lessons, command discoveries, explanations, and small demonstrations.
- [`investigations/`](investigations/) — bounded questions with exact sources, commands, evidence, and limits.
- [`templates/`](templates/) — starter documents for notes and investigations.
- [`upstream/`](upstream/) — imported source trees used for reading, testing, and candidate patches.

## Working surfaces

**Research rounds map possible directions.** They organize promising questions, source targets, first probes, environment requirements, promotion signals, and stop signals before a lane becomes active work.

**Notes capture reusable understanding.** Use them for concepts, commands, operational recipes, source-reading lessons, and behavior that can be demonstrated without a full research record.

**Investigations test bounded questions.** They record the source revision, environment, baseline behavior, hypothesis or candidate change, reproduction commands, results, interpretation, evidence boundary, and next step.

**Imported source trees support real code work.** They provide a preserved upstream revision for reading, testing, and candidate changes.

A research lane can become an investigation when its source boundary and distinguishing probe are clear. A note can become an investigation when its claim needs stronger verification. An investigation can link back to research rounds and notes that explain the surrounding Linux concepts.

## Working source trees

Imported upstream projects live under `upstream/`. Their original files, licensing information, and executable permissions are preserved. Import metadata records the upstream repository, requested revision, resolved commit, and import time.

## Evidence discipline

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

- [`RESEARCH_LANES.md`](RESEARCH_LANES.md) — active shortlist and environment queues.
- [`research/`](research/) — dated landscape rounds and possible investigation lanes.
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
