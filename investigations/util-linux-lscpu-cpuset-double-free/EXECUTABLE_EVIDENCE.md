# Executable evidence for the util-linux cpuset ownership fix

State: `current-main candidate — exact-head CI pending`

## TL;DR

The canonical source owner and upstream correction are already mapped in `README.md`. This companion record retains the executable ownership distinction and requires an exact reviewed v2.41 fixture before the upstream patch is applied.

No new util-linux implementation is proposed.

## Explain like I'm five

The source map identifies who forgot to erase a freed pointer. The small executable model proves why erasing it matters, without deliberately crashing or freeing real memory twice.

## Exact carrier

- canonical upstream patch with original authorship;
- minimal v2.41 `lib/path.c` error-path fixture;
- deterministic C ownership model;
- compiler/runner;
- focused unit regression.

Imported util-linux source is not added or modified.

## Ownership model

The model preserves this sequence:

```text
parser publishes allocation
→ parse error frees allocation
→ caller still holds output pointer
→ ordinary outer cleanup reaches it again
```

A tracker records logical cleanup instead of calling real `free()` twice.

The runner builds with:

```text
-std=c11 -Wall -Wextra -Werror
```

Expected results:

- baseline: duplicate cleanup detected, status 42;
- candidate with `CLEAR_OUTPUT_AFTER_ERROR`: output becomes NULL, later cleanup harmless, status 0.

## Exact retained patch and fixture contract

`0001-clear-cpuset-output-after-error.patch` preserves canonical util-linux commit `4581ede384f22983d6155768635ce43cb5304cb0` and adds:

```c
cpuset_free(*set);
*set = NULL;
```

The fixture is intentionally a minimal extraction rather than a thousand-line copy of `lib/path.c`. The canonical hunk header therefore reports a large line offset even when the fixture bytes are correct. Zero offset is not a meaningful requirement for this reduction.

The current regression instead requires:

1. the complete fixture bytes equal the reviewed literal source before patch execution;
2. dry-run and real application use `--fuzz=0`;
3. neither application may report fuzz;
4. the exact post-patch free-then-NULL sequence is present;
5. a one-line fixture drift fails the identity check before patch execution.

This keeps the source boundary exact without padding the fixture with meaningless lines or rewriting the canonical upstream hunk header.

## Required gate

- Python compilation;
- complete repository unit discovery;
- baseline/candidate C model;
- exact fixture identity;
- zero-fuzz dry-run and real patch application;
- fixture-drift losing control;
- complete six-file diff review;
- current-main relation and mergeability.

Historical predecessor head `247d26c3a96a0bb5cc001950d899f32d8b961eba` passed Linux Fieldwork CI `30589924810` / 700 before fixture-identity tightening. That run is mechanism provenance only.

## Evidence boundary

Established:

- deterministic stale-output-pointer ownership distinction;
- exact reviewed fixture bytes and canonical hunk content;
- NULL-safe ordinary cleanup after the repair.

Not established:

- execution of report 4401's archive;
- Debian trixie package behavior;
- ASan or Valgrind results against util-linux;
- full `lscpu` output compatibility;
- current downstream update state.

Those package-level questions remain separate from this source-ownership evidence.

## Disposition and authority

**MERGE LOCALLY** after fresh exact-head CI and complete review. Any Debian package verification or external contact remains **HOLD** pending a deliberate authorization decision.

Internal Linux Fieldwork evidence only. No external issue, email, patch submission, merge request, comment, release, or deployment is authorized or included.

Refs canonical map `README.md`, issue #234, and historical PR #239.
