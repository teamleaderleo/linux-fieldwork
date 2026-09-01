# Product prototype audit

Updated: `2026-08-02`  
Controlled fork PR: `teamleaderleo/systemd#2`  
Prototype branch: `linux-fieldwork/oomd-reporter-source-precedence`  
Current audited head: `e4e96e23b57889128ff0fa347d3b77bd525fe3ea`  
Replacement focused run: `30755298324`  
External contact: `false`

## Scope under review

The first product slice separates source classes into six contribution maps:

```text
SYSTEM_MANAGER × {swap, memory pressure, rules}
USER_MANAGER   × {swap, memory pressure, rules}
```

The existing monitored maps remain the effective runtime view. System-manager contributions take precedence, and complete tuples are selected without field-wise mixing.

This is deliberately not the final authority model. Per-UID user authorities and connection-lifetime cleanup remain separate follow-on work.

## Pre-CI defect found

The initial generated prototype mutated a source contribution before recomputing effective state:

```text
mutate source map
        ↓
allocate/copy effective state
        ↓
possibly fail
```

For `OOMRules`, `strv_copy()` could return `-ENOMEM` after the source contribution had already changed. The receive path then logged the recomputation failure and continued, leaving:

```text
source contribution = new tuple
effective context   = old tuple or partially inserted context
```

No later message is guaranteed to repair that divergence. This violated the atomic update contract already encoded in `model_policy.py` and `test_model_atomicity.py`.

## Atomicity correction

The fail-closed wrapper now transforms the generated C so that updates behave transactionally.

### AUTO withdrawal

The effective result is staged while the withdrawing reporter's old contribution is still present but explicitly ignored by reduction:

```text
recompute as if sender contribution were absent
        ↓
if successful, remove sender contribution
```

Source removal is performed only after all fallible effective-state work completes.

### Explicit update

For an existing contribution:

- pressure limit and duration are snapshotted;
- the old rule list is moved into a rollback owner;
- the new tuple is installed;
- effective state is recomputed;
- on failure, the exact previous tuple is restored.

For a newly inserted contribution:

- insertion is tracked;
- on recomputation failure, the new contribution is removed and unref'd.

### Effective OOMRules allocation

The selected rule list is copied before inserting or mutating an effective context. After that allocation succeeds, the remaining effective transition is non-fallible under the current helpers.

### Failure behavior

- `-ENOMEM` rolls back and propagates;
- other recomputation errors roll back, log, and skip the malformed element;
- source and effective maps remain aligned.

## Additional review findings

### Correct behavior retained

- system-manager precedence selects one complete pressure tuple;
- user `auto` cannot delete a system contribution;
- system withdrawal can reveal the already-live user contribution;
- no-op effective pressure tuples preserve `mem_pressure_limit_hit_start`;
- ruleset start times are removed only for rules leaving the effective list;
- source maps use `oomd_cgroup_ctx_hash_ops`, matching existing value ownership.

### Known limitations that remain deliberate

1. User contributions are grouped by source class rather than `(USER_MANAGER, uid)`.
2. Varlink links are not yet tracked as generations.
3. Last-link disconnect does not withdraw user contributions.
4. PID 1 subscription termination does not withdraw system contributions.
5. Cgroup disappearance does not explicitly purge durable source contributions.
6. `oomctl` does not expose effective source or contributors.
7. The contribution maps store full `OomdCGroupContext` objects even though only policy fields are required; the final reducer should use dedicated policy values.

These prevent this slice from being an upstream-shaped final patch, even if its focused tests pass.

## Execution identity caveat

The current source-precedence workflow still uses the default pull-request checkout, so its receipt will identify GitHub's synthetic merge commit rather than the direct branch head.

The product diff remains attributable because the base is canonical `main@6a863b4dc31adc49fdfdd5deba32ed1b115adda3` and the fork branch contains only controlled evidence tooling. However, a successful result must be described as merge-derived until the workflow is revised to check out and verify the PR head explicitly.

Do not label run `30755298324` an exact-head execution unless its checkout step is corrected before it starts.

## Replacement gate

The earlier queued run `30755078046` belongs to pre-hardening head `7186e5a140df4f646e9bd0ceb90302c6c362dc16` and is stale for product conclusions.

Current validation target:

```text
head: e4e96e23b57889128ff0fa347d3b77bd525fe3ea
run:  30755298324
```

Required results:

- fail-closed source transformation;
- `git diff --check`;
- `systemd-oomd` compile with `--werror`;
- existing `test-oomd-util` pass;
- reported reload regression fixed;
- 50% system tuple remains effective against a 70% user tuple;
- system withdrawal reveals the live 70% user tuple;
- final user withdrawal removes the effective path;
- product diff and guest journal retained.

No pass is claimed until the exact job logs and artifact are inspected.

## Next product slice

After the hardened first slice is green:

1. replace the six source-class maps with dedicated contribution values;
2. key user authority by UID;
3. track live Varlink connection generations;
4. withdraw contributions on last disconnect;
5. handle PID 1 stream termination and initial-snapshot restoration;
6. purge source state on cgroup disappearance;
7. expose source diagnostics;
8. add focused C reducer tests before broad manager integration.

## Authority

All review, code generation, and execution remain inside `teamleaderleo`-owned repositories. No action was taken in `systemd/systemd`.
