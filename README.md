# Linux Fieldwork

A GitHub-hosted workbench for investigating Linux and Debian projects from a phone-first workflow.

> **Current work:** use live GitHub issues and pull requests together with programme/target state and the owning evidence records. [`CURRENT_FIELDWORK.md`](CURRENT_FIELDWORK.md) is a retired historical board retained only as a Git-history pointer.

## What lives here

Linux Fieldwork is a lab notebook and working copy for learning Linux behavior, mapping research directions, testing bounded questions, and preparing candidate fixes.

- [`programmes/`](programmes/) and [`programmes/registry.yml`](programmes/registry.yml) hold long-lived research directions and formal lanes.
- [`targets/`](targets/) and [`targets/registry.yml`](targets/registry.yml) map recurring upstream projects, exact source identity, related lanes, investigations, and contribution boundaries.
- [`research/`](research/) retains dated landscape and selection reasoning.
- [`notes/`](notes/) keeps reusable concepts, commands, recipes, demonstrations, and source-reading lessons.
- [`investigations/`](investigations/) carries exact-source questions, repeatable evidence, candidate changes, results, limits, and next steps.
- [`upstream/`](upstream/) contains imported project trees for source reading, testing, and candidate work; import metadata preserves the upstream repository, requested revision, resolved commit, and import time.

A possibility can move from a research round into a programme lane, then into an investigation when exact source work begins. General lessons can move into notes at any stage. See [`START_HERE.md`](START_HERE.md) for the work-type router.

## Start with the owner you need

- [`START_HERE.md`](START_HERE.md) — choose the smallest useful record and preserve reproducible evidence.
- [`AGENTS.md`](AGENTS.md) — agent authority and routing.
- [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md) — collaboration, checkpoints, recovery, review, and third-party GitHub reference hygiene.
- [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) — rules that begin only after a human designates an owned-fork branch or commit series as an upstream candidate.
- [`WRITING.md`](WRITING.md) — reader-facing technical writing.
- [`FIELD_GUIDE.md`](FIELD_GUIDE.md) and [`BUG_LENSES.md`](BUG_LENSES.md) — practical review and investigation heuristics.
- [`SECURITY_RECONVENE.md`](SECURITY_RECONVENE.md) — the exceptional disclosure-sensitive reconvene boundary.

## Evidence discipline

The repository should carry enough current state for another worker to resume without the chat. Durable technical claims should identify the exact source or retrieval boundary, relevant environment and tool versions, repeatable commands or steps, baseline and candidate behavior when applicable, observed results separately from interpretation, evidence limits, and upstream-contact state. Preserve useful negative results too.

Imported source trees keep original files, licensing information, and executable permissions. Exact commits, artifacts, and tracked records are the durable identity of the work.

## Upstream boundary

Research, local patches, and candidate changes stay inside controlled `teamleaderleo` repositories and forks until a deliberate decision authorizes an upstream issue, email, merge request, patch submission, comment, review, or other third-party interaction. Agent research authority is defined in [`AGENTS.md`](AGENTS.md); backlink and collaboration rules are owned by [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md).
