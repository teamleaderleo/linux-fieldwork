# Start Here

Use this runbook whenever a person or agent is asked to add Linux learning, map a research direction, or investigate a Linux or Debian project through this repository.

Read [`WRITING.md`](WRITING.md), [`FIELD_GUIDE.md`](FIELD_GUIDE.md), and [`BUG_LENSES.md`](BUG_LENSES.md) alongside this runbook for current prose guidance, practical review lessons, recurring defect classes, and investigation methods retained from prior work.

## In simple words

Choose the smallest useful record. Write a note for reusable understanding. Use the programme registry for a plausible formal direction. Give a lane its own directory when its bounded question and first probe are clear. Open an investigation when exact source work and repeatable evidence begin.

A reader should understand the question, consequence, and proposed answer before meeting the test matrix.

## 1. Check existing work

Search, in order:

1. [`programmes/registry.yml`](programmes/registry.yml) and the relevant programme `STATUS.md`;
2. [`targets/registry.yml`](targets/registry.yml) and any target map;
3. `research/rounds/` for prior landscape reasoning;
4. `notes/` for reusable explanations;
5. `investigations/` for active or retained evidence;
6. the relevant imported tree under `upstream/`.

Link related records instead of repeating them. Existing work is context, not permission: a claim, assignee, branch, or pull request does not reserve the question. Parallel reproduction, review, and competing candidates are allowed. Use separate exact heads, compare the results, and retain the evidence that explains which variant survived.

Immediately before writing to an issue, pull request, or branch, refresh the canonical carrier, latest disposition, exact head, and current-main relation. This is an identity check, not an ownership lock. A technically useful branch may have become retired provenance while a newer restack owns the decision.

When a gate fails, classify the first distinguishing owner before changing product code: product, fixture, capability, workflow, tooling, packaging, or evidence. Repair the owner that prevented the intended observation, then rerun unchanged downstream logic.

### Make a bounded cross-context pass

Before narrowing to one file or one happy path, sample the adjacent contexts that could change the decision: caller and callee, direct and mediated paths, producer and consumer, setup and cleanup, sibling modes or backends, representation and metadata, ownership, nearby tests, and relevant history.

When behavior looks wrong, ask first: **what evidence would make this behavior correct, intentional, or required?** Search for that evidence before promoting a defect claim. Check:

- relevant history, blame, old fixes, reverted changes, comments, and release notes;
- nearby tests and project conventions;
- callers, callees, wrappers, hooks, package scripts, services, and downstream consumers;
- sibling modes, distributions, architectures, privilege levels, namespaces, and chroot or chrootless execution;
- man pages, Debian policy, protocol or archive specifications, schemas, exit-status conventions, and other applicable contracts;
- compatibility behavior or old workarounds whose purpose is easy to miss in the local implementation;
- differences in operation owner or authority that can make similar-looking paths intentionally behave differently.

If that pass explains the behavior, sharpen the claim or retain a negative result. If the invariant still fails, ask: **what adjacent context could overturn the current explanation of why it is wrong?** Give those contexts explicit discriminators before widening a patch or claiming a general defect.

Choose two to four adjacent contexts. Give each one a discriminator that could make the current mechanism, compatibility claim, evidence boundary, or next action lose. Transfer reusable defect classes from other investigations—identity, ordering, completeness, cleanup authority, sanitizer bootstrap, metadata, retry, cache, and exact-execution mistakes—but keep them as hypotheses with negative controls.

When an adjacent context invokes the same executable or resembles the same mechanism, verify that it has the same operation owner and authority contract before widening the patch. A host probe, user-directed hook, sanitizer, and package child may all call the same tool for intentionally different reasons. Broad review may produce a new defect, a separate successor, or a sharper boundary; it does not have to produce a larger patch.

Breadth is not permission for aimless exploration. Record a stop condition. Stop when the selected contexts cannot change the decision, or split a distinct finding into its own carrier instead of silently widening the current patch. Follow [`notes/processes/cross-context-review-prevents-myopia.md`](notes/processes/cross-context-review-prevents-myopia.md) for the review map and compact receipt, and [`notes/processes/recent-cross-context-lessons.md`](notes/processes/recent-cross-context-lessons.md) for recent examples involving carrier freshness, failure ownership, structured argv evidence, adjacent authority, and workflow state.

## 2. Choose the work type

Use a **note** for:

- a Linux concept explained clearly;
- a command or workflow worth remembering;
- a small demonstration;
- a source-reading lesson;
- a distribution-specific detail with clear version limits.

Use a **registry lane** for a plausible formal question whose source target or first probe still needs mapping.

Use a **formal lane directory** when:

- the question is bounded;
- likely source targets are named;
- the environment and privilege requirements are known;
- one first probe has distinguishing outcomes;
- a meaningful promotion signal exists;
- a clean stop signal exists.

Use an **investigation** for:

- execution against an exact source or package revision;
- a suspected defect or surprising behavior;
- a candidate patch;
- a compatibility, performance, security, or lifecycle claim;
- work that may eventually be offered upstream.

Start notes and investigations from [`templates/`](templates/). Follow [`programmes/README.md`](programmes/README.md) for formal lane promotion.

## 3. Explain it for a human reader

Near the top, make three reader needs easy to recover:

- **current answer or concrete question**;
- **understandable mechanism**;
- **practical consequence**.

Use the representation that earns its space. `## In simple words`, `## TL;DR`, `## Why care`, a state trace, a before/after snippet, or a small table can all do the job. `## Explain like I'm five` is available when that voice genuinely helps. [`WRITING.md`](WRITING.md) is the current rule; the repository no longer requires a fixed three-heading ritual for every investigation.

For a defect, candidate, or surprising behavior, make these answers visible:

- What does the component do, and where does it sit?
- What exact input and action produce the wrong result?
- Who or what receives the consequence?
- What does source or history show about intent?
- What changes, why is that boundary appropriate, and what remains open?

Prefer a literal example such as `origin promises 100 bytes → sends 40 → candidate removes the temporary file` over a phrase such as “response handling is hardened.” Define specialized terms at first use.

Keep observed behavior, intent evidence, interpretation, design choice, and future work distinct. Preserve useful author cadence instead of rewriting every record into the same house rhythm.

## 4. Record the source boundary

For code or package work, record the project, requested revision, resolved commit or package version, local path, and import metadata path. Preserve upstream licenses and executable permissions.

For general system behavior, record the distribution, release, kernel, architecture, shell, privileges, container or virtual-machine context, and relevant tool versions.

Update or create a target map when one upstream project becomes recurrent across several lanes or investigations.

## 5. Run the smallest useful demonstration

Prefer a command or test that preserves the important behavior while remaining easy to repeat. Capture the exact command, expected distinguishing outcomes, actual result, and cleanup steps.

For a candidate change, compare baseline and candidate behavior under the same conditions. Use the donut checks in [`FIELD_GUIDE.md`](FIELD_GUIDE.md) and the invariant-first method in [`BUG_LENSES.md`](BUG_LENSES.md) to look for missing permission, path, metadata, lifecycle, compatibility, and evidence boundaries around the headline result.

When useful, use this search sequence:

1. state the invariant and at least one competing explanation;
2. choose a discriminator such as differential testing, reduction, bisection, fault injection, signal or schedule perturbation, property testing, or an independent oracle;
3. include a negative control;
4. find the earliest meaningful divergence between good and bad behavior;
5. reduce the failing case until the operation owner becomes clear;
6. perturb timing, state, environment, privilege, retries, interruption, or ordering where relevant;
7. inspect surviving processes, files, modes, mounts, sockets, locks, package records, environment, and metadata;
8. run the same operation cleanly again;
9. ask which nearby assumption could produce the next defect in the same family.

Each important plain-language claim should map to a command, fixture, source line, or observed result.

## 6. State the evidence boundary

Say exactly what the work establishes and where the conclusion ends. Mention skipped test suites, untested platforms, privilege assumptions, mocked components, reduced fixtures, and environment-specific behavior.

When the distinction could be unclear, label a conclusion as demonstrated behavior, plausible consequence, design choice, or open question.

## 7. Preserve progress and reconvene when needed

If a chat response, connector call, command, hosted job, or safety check stops, separate that interruption from product behavior. Use the `INTERRUPTION CHECKPOINT` in [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md), then resume from the exact repository head, raw artifacts, current receipts, and tracked records rather than chat narration.

For security-related work, read [`SECURITY_RECONVENE.md`](SECURITY_RECONVENE.md). It distinguishes ordinary repairable findings from the uncommon all-red case where a result begins to look like a serious vulnerability or disclosure event and public logging should stop.

Security-adjacent work does not automatically require `RECONVENE`. Continue ordinary investigation and repair when the work stays on public source, local or owned systems, synthetic fixtures, disposable state, and authorized repository actions. Typical examples include local path traversal with fake destructive commands, malformed-input crashes, signal and cleanup defects, wrong-result bugs, permission mistakes, and defense-in-depth hardening with restrictive prerequisites.

Do not use a hard 7/10, 8/10, or 9/10 cutoff. Severity estimates are context only. Judge the real operation, authority crossed, deployment reach, ease of exploitation, publication delta, and whether the current public workflow remains an appropriate surface.

Switch to `RECONVENE` only when the investigation reaches a materially different boundary: real secrets or private data, a live public target, an unauthorized authentication or authorization bypass on a real system, destructive or persistent capability, unusually broad or low-friction impact, or operational detail that cannot safely remain in the current public record. Preserve a public-safe checkpoint, finish cleanup, stop deepening that path, and request a specific human decision about sanitized continuation, private handling, upstream contact, or stopping.

## 8. Decide the next step

Choose one:

- retain or expand a note;
- keep a possibility in the programme registry;
- promote a possibility into a formal lane directory;
- open or continue an investigation;
- keep a local candidate change;
- prepare an upstream packet after explicit authorization;
- close with a negative result.

For a merge or upstream decision, say what the reviewer is choosing and which exact evidence supports that choice.

## Upstream contact

Programme, lane, target, research, note, and investigation records grant no authority to contact maintainers. External issues, email, merge requests, patches, comments, and reviews require a deliberate decision.

Before posting or editing any GitHub interaction surface in a controlled repository — including internal fork pull-request titles or bodies, issue comments, reviews, and discussions — convert third-party GitHub issue, pull-request, discussion, and commit references to `https://redirect.github.com/...`. Do not use direct `https://github.com/OWNER/REPO/issues/...` or `.../pull/...` links, and do not use bare `OWNER/REPO#123` shorthand merely to cite evidence: those forms can create upstream timeline backlinks even when the interaction itself is in a controlled fork.

If a direct third-party reference is posted accidentally, edit the originating controlled-repository interaction surface to redirect form immediately. Repository files may still use direct third-party links because they do not create GitHub issue or pull-request cross-reference events. See [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md#external-github-backlinks) for the full rule.
