# Deep dive — final projected identity for type-excluded hard links

## Question and demonstrated failure

When a type filter removes an archive member before component stripping and transforms run, which identity decides whether a later retained hard link still has a target?

The PR #310 predecessor stores normalized input names. Extractors resolve hard links against emitted names. That mismatch creates a demonstrated false rejection:

1. retain regular `prefix/base`;
2. exclude symlink `root/base`;
3. retain hard link `root/peer -> root/base`;
4. apply `--type-exclude=SYMTYPE --strip-components=1`.

The predecessor rejects `root/peer -> root/base`, although output rewriting would produce valid `base` plus `peer -> base`. The selected candidate uses final projected identities and emits an extractable one-inode result.

## Exact source mechanism

The composed stream processes each member through these logical operations:

1. path filtering;
2. type filtering;
3. member and hard-link target component stripping;
4. PAX filtering and ID shifting;
5. scoped transforms;
6. output.

Patch 0001 adds normalized names removed by type, names actually retained, first-known dependency rejection, and loop break followed by normal tar-context close and status 1. Its dependency check occurs before steps 3 through 5. Its retained update occurs after those steps but uses a saved input identity. Lifecycle timing is correct; identity timing is wrong.

Patch 0002 introduces one `rewrite_name()` path backed by unit 15's `_sed_substitute`:

- excluded members use member-name scope `r`;
- retained member names use scope `r`;
- retained hard-link targets use scope `h`;
- symlink text follows scope `s` and does not enter hard-link availability state;
- a strip result with too few components returns no projected identity.

The dependency decision compares normalized final projected identities. The diagnostic prints the original input member and target strings.

## Selected invariant

A retained hard link is accepted when its final projected target identity is already available among retained final member identities.

A type-excluded occurrence marks only its surviving final projected member identity unavailable, and only while no retained occurrence supplies that same identity.

A known unavailable dependency stops before the hard-link member is written. The tar stream finalizes before status 1.

## Reproduction and result matrix

### Valid final target previously rejected

Input:

```text
regular prefix/base
symlink root/base -> missing
hard link root/peer -> root/base
```

Options:

```text
--type-exclude=SYMTYPE --strip-components=1
```

Predecessor returns status 1 and a finalized partial archive containing regular `base`.

Selected candidate returns status 0, emits regular `base` and hard link `peer -> base`, and GNU tar extracts one inode.

### Genuine removed final target

Input regular `root/base` followed by hard link `root/peer -> root/base`; option `--type-exclude=REGTYPE`.

Selected candidate returns status 1, retains the original-name diagnostic, emits no hard-link member, and finalizes a valid empty archive.

### Strip-dropped target and dependent link

A one-component target name and hard-link target are both dropped by `--strip-components=1`. Input-name state previously rejected. Final projection produces no target identity and no retained hard-link member, so the selected candidate returns status 0 with a valid empty archive.

## Attribution boundary

### Strip-only reference failure

Input regular `root/base` and hard link `prefix/peer -> prefix/root/base`. `--strip-components=1` already emits regular `base` and broken hard link `peer -> root/base`. GNU tar extraction fails without type exclusion. Unit 16 preserves that result and leaves the general rewrite behavior with unit 15.

### Transform `H` scope failure

`--transform=s,^root/,,H` transforms member names while leaving hard-link target text unchanged. The direct archive is already broken. Type exclusion does not claim this dependency through intermediate aliases.

These controls reject a broader “any alias ever seen” policy.

## Approach history

### Member-local type filtering

PR #244 demonstrates status 0 with a dangling hard link. Rejected for the tarfilter-specific type option.

### Input-name focused rejection

PR #248 catches a genuine target-before-link removal but originally interrupted archive finalization and mishandled duplicate names. Superseded by PR #310.

### Finalized rejection and retained duplicate state

PR #310 closes the output stream before status 1, preserves an earlier retained target across a later excluded duplicate, and updates retention after later skip decisions. Selected as patch-0001 predecessor.

### Alias projection

Alias projection stored input, post-strip, and post-transform aliases. It passed all 442 tests in run `30690434953`. Direct controls prove over-attribution: it reports a type-filter failure for an archive already broken by strip processing. Rejected and retained under `patches/rejected/`.

### Final projected identity

Final projected identity stores one surviving final identity per excluded or retained member, uses hard-link target scope for retained references, and preserves original strings for diagnostics. Selected.

## Clean prerequisite selection

The historical PR #68 patch records reviewed transform and target-scope behavior, yet its parser hunk does not apply with zero fuzz to exact imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`. Runs `30689716762`, `30690001217`, and `30690165287` preserve that packaging evidence.

Unit 15 regenerated the transform/metadata candidate against the imported blob. Unit 16 retains that exact patch as 0000 and generates patches 0001 and 0002 for its five-field transform tuple and `_sed_substitute` helper.

## Compatibility analysis

### Content and links

Valid retained targets preserve content and inode identity. Removed targets produce no dangling member.

### Status and stderr

Known type-owned dependency breaks return status 1 with:

```text
hard-link target excluded by type filter: MEMBER -> TARGET
```

`MEMBER` and `TARGET` are original input strings. Final projected identities remain internal decision state.

### Archive lifecycle

The loop breaks at the first known dependency. The output context writes its trailer before the process exits 1. Partial or empty output remains syntactically valid.

### Duplicate and collision semantics

A retained final identity clears an unavailable marker and remains available across later excluded duplicate occurrences. Transform collisions are handled in the same final identity domain. Set semantics are sufficient for target-before-link streaming because one retained occurrence supplies the extractor-visible target.

### Prefix normalization

Repeated leading `/`, `./`, and `../` components compare as GNU tar-equivalent archive-root spellings. `.../` remains distinct. The direct invalid control for `.../root/base` stays allowed.

### Independent type filters

Excluding hard links alone leaves a transformed regular target and extracts successfully. Excluding both regular and hard-link types produces an empty archive. The successful control runs twice immediately.

### PAX metadata

Unit 15 clears stale `path` and `linkpath` when names change. Unit 16 reuses that behavior and adds no encoding policy.

### Streaming and memory

The candidate preserves target-before-link streaming and stores archive-sized name sets. Link-before-target order and arbitrary graph buffering stay excluded.

### Path filters

Dpkg-compatible path filtering remains unchanged.

## Executed evidence

### Selected focused gate

Run `30690541675`, job `91344358024`, exact head `ec55994f0db12044f9c7ef9f843fe42aec7393e6` validated 4 patch files and 11 hunks, compiled, passed 442 tests, and passed shell and command-help gates.

### Inherited gate

Run `30690583438`, job `91344466738`, head `300b51056ded64a56ec3998bc639a57e9ea81125` validated the same active series, compiled, passed 450 tests, and passed shell and command-help gates.

That run also exposed four accidental duplicate focused tests through a module-level class alias. Commit `7fe46662141fa39a3b18ae1baba29b2b39f6c330` changes the import to a module reference. The clean expanded rerun is `30691015678`.

## Complete branch review

Comparison with `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` shows exactly 14 added files:

- 2 executable test modules;
- 8 packet records and drafts;
- 3 active ordered patches;
- 1 rejected patch retained as evidence.

The branch does not modify the imported tarfilter directly. The patch series remains the source candidate.

## Why the patches belong together

Patch 0002 depends on the rewrite semantics and `_sed_substitute` introduced by patch 0000, and it replaces the input-name state introduced by patch 0001. Reviewing the final identity rule without those exact prerequisites would hide its behavior and hunk ownership.

For upstream delivery, the human reviewer may choose one integrated source commit or an ordered series. The packet preserves the three logical layers for review and rebase.

## Remaining work

1. complete clean expanded run `30691015678` and confirm 449 discovered tests;
2. run one unchanged-head complete rerun;
3. fetch current Salsa `master`, record its exact commit, and rebase the series with zero fuzz;
4. complete final diff review against that base;
5. create or select a controlled Salsa fork only after authorization;
6. update submission drafts with final upstream identities.

## Evidence boundary

Executed evidence covers the imported tarfilter, Python tarfile-generated fixtures, GNU tar extraction, target-before-link ordering, Linux Fieldwork CI on Ubuntu 24.04, and the declared strip/transform/type matrix. Package pipelines, other extractors, other platforms, privileged metadata, link-before-target order, and arbitrary graphs remain outside the demonstrated claim.

## Authority

Internal Linux Fieldwork work only. External contact remains unauthorized and absent.
