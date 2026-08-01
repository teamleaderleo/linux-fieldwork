# Deep dive — final-name identity for type-excluded hard-link targets

## Question and observed failure

When `tarfilter` removes a member by type, then later rewrites archive member names and hard-link targets through component stripping or transforms, which name domain decides whether a retained hard link still has an emitted target?

The current composed predecessor uses normalized input names. The emitted archive uses rewritten names. Issue #335 identifies both error directions created by that mismatch.

## Source mechanism

The imported loop performs decisions in this order:

1. path filter;
2. type filter;
3. component stripping;
4. PAX filtering and ID shift;
5. transforms;
6. output.

The PR #68 carrier extends steps 3 and 5 so hard-link targets follow member-path rewrites and stale PAX reference metadata is removed.

PR #248 records normalized names skipped at step 2 and checks a retained hard-link target immediately after step 2. PR #310 adds retained-name state and moves successful retention updates immediately before output, while preserving the early dependency check. Timing of retained state is correct; the checked identity still belongs to the pre-rewrite input domain.

## Reproduction narrative

### False rejection

Input order:

1. regular `prefix/base`;
2. type-excluded symlink `root/base`;
3. hard link `root/peer -> root/base`.

Options:

```text
--type-exclude=SYMTYPE --strip-components=1
```

The emitted regular target becomes `base`. The hard link would become `peer -> base`. The predecessor sees excluded input identity `root/base` before rewriting the hard-link target and stops with status 1. Its finalized partial archive contains only `base`.

A direct expected archive containing `base` and `peer -> base` extracts successfully and preserves one inode, proving the rejected dependency is valid in final-name space.

### False acceptance

Input order:

1. type-excluded regular `root/base`;
2. hard link `prefix/peer -> prefix/root/base`.

Options:

```text
--type-exclude=REGTYPE --strip-components=1
```

The predecessor compares `prefix/root/base` against excluded input identity `root/base` and allows the hard link. Component stripping then emits `peer -> root/base`. No `root/base` member exists in output. The filter returns status 0 and GNU tar extraction fails.

## Approach history

### Approach A — member-local filtering

- Mechanism: skip each matching type independently.
- Evidence: PR #244 exact-head execution.
- Result: status 0 with a dangling hard link after removing its regular target.
- Disposition: rejected for this tarfilter-specific type option.

### Approach B — focused input-name rejection

- Mechanism: remember normalized type-skipped input names and reject retained hard links targeting them.
- Evidence: PR #248 candidate matrix.
- Result: catches target-before-link dependency breaks and preserves independent type filters.
- Cost: early `exit(1)` originally interrupted archive finalization; raw exclusion state ignored retained duplicate names.
- Disposition: superseded by PR #310 repairs.

### Approach C — finalized rejection plus retained duplicate state

- Mechanism: break the loop, close the tar stream, exit afterward; track names actually retained and keep an earlier target available across an excluded duplicate.
- Evidence: PR #310 carrier and focused duplicate/strip-skipped tests.
- Result: repairs output lifecycle, valid duplicates, and premature retention updates.
- Cost: dependency check and exclusion identity remain pre-rewrite.
- Disposition: retained as the predecessor for unit 16.

### Approach D — final emitted-name state

- Mechanism: project excluded occurrences and retained hard-link targets through the same rewrite operation used for output, then compare availability in one final-name domain.
- Evidence: issue #335 design direction; unit 16 two-case discriminator.
- Result: pending candidate implementation and execution.
- Compatibility requirements: preserve transform target scopes, PAX cleanup, duplicate handling, finalized failure output, and target-before-link streaming.
- Disposition: selected direction for the next candidate.

## Selected correction constraints

The correction should introduce one explicit rewrite path that can be applied consistently to:

- a retained member name before output;
- a retained hard-link target before dependency checking;
- a type-excluded member name for availability projection.

The function must express whether rewriting drops the identity entirely, as component stripping does for paths with too few components. It must honor transform target scopes: excluded member projection follows member-name scope, while hard-link target projection follows hard-link scope.

State should represent final emitted target availability. Duplicate occurrences require reference-count or equivalent occurrence-aware handling if later output-name collisions can add or remove availability. The first bounded candidate may retain set semantics only after executable collision controls establish that one retained occurrence is enough and excluded later occurrences cannot erase it.

## Why the changes belong together

Type exclusion creates the unavailable-target event. Strip and transform operations define the final identity used by archive extractors. Hard-link dependency validation becomes correct only when those operations share one naming contract. Splitting the final-name projection from the dependency check would preserve the current mismatch.

## Compatibility analysis

### Bytes and logical content

A valid retained target plus hard link should remain extractable with shared content and inode identity. A missing target should produce status 1 before the broken member is written.

### Status and stderr

The focused diagnostic remains:

```text
hard-link target excluded by type filter: MEMBER -> TARGET
```

The displayed names need a deliberate policy: original input names are useful for diagnosis, while the decision uses final rewritten identities. The candidate should retain original names for the message unless tests reveal ambiguity.

### Archive lifecycle

The output tar context must close before status 1. A rejected first dependency leaves a finalized partial or empty archive.

### Metadata

Member and hard-link target rewrites must clear stale PAX `path` and `linkpath` exactly as the PR #68 carrier does. Unit 16 adds no independent PAX encoding policy.

### Streaming and memory

Target-before-link handling can remain streaming with archive-sized name state. Link-before-target support requires buffering and stays outside this unit.

### Path-filter semantics

Dpkg-compatible path filtering remains unchanged. This unit acts only on `--type-exclude` dependency state.

## Rejected alternatives

### Silently skip the dependent hard link

This removes an allowed member and hides the dependency decision.

### Materialize target bytes

This changes hard-link semantics, requires payload retention, and widens memory ownership.

### Buffer arbitrary graphs

This expands the unit beyond the valid target-before-link baseline and changes the streaming model.

### Compare both raw and final strings

Dual-domain acceptance can hide contradictions and permit broken output when either spelling happens to match. One final emitted-name domain gives a coherent invariant.

## Open discriminators

1. Exact execution of both strip cases on the packet-composed predecessor.
2. Transform-scope controls for excluded-name projection and hard-link target projection.
3. Output-name collision controls across duplicate retained and excluded occurrences.
4. Full inherited PR #248 and PR #310 matrices on the selected correction.
5. Complete current-main CI after cleanup and immediate rerun.

## Evidence boundary

Current packet evidence covers source and carrier review plus prepared executable characterization. Package pipelines, other extractors, other platforms, privileged metadata, link-before-target order, and arbitrary dependency graphs remain unexecuted or excluded.

## Authority

Internal Linux Fieldwork work only. External contact remains unauthorized and absent.
