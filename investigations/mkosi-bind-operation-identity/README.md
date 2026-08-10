# mkosi sandbox bind-operation identity drops behavior-changing flags

## TL;DR

At `systemd/mkosi` commit `f7401bdc8d23486bb346790dc92508381a062f3b`, `BindOperation.__hash__()` omits the behavior-changing `foreign` and `relative` fields, while `__eq__()` defines equality as equal hashes. `FSOperation.optimize()` first inserts bind operations into a dictionary, so two otherwise identical binds that differ only in either omitted field collapse to one operation and the first operation's semantics survive. A reduced execution of the exact identity/optimizer logic reproduces the order-dependent collapse. The next gate is an end-to-end `mkosi-sandbox` CLI fixture against the exact upstream head before promoting this from source/reduced-fixture evidence to a runtime defect claim.

## Explain like I'm five

The sandbox makes a list of filesystem mounts, then removes duplicates before doing them. Two mounts can look the same on paper but mean different things: one can map a foreign UID range, and one can interpret its source relative to the new sandbox root. Those choices are currently missing from the duplicate key.

Literal example: `normal bind /src -> /dst` followed by `foreign bind /src -> /dst` enters the optimizer; the reduced fixture returns only the first normal bind. Reversing the order returns only the foreign bind.

## Why care

The affected code is `mkosi/sandbox.py`. `foreign` controls whether a bind is prepared through a transient user namespace and contributes to the later delegated-range decision. `relative` changes which root `chase()` uses for the source. Collapsing operations that differ in either field can therefore change which object is mounted or whether foreign-ID mapping is performed.

## Current state

- State: `EXECUTING`
- Exact working head: fieldwork branch `linux-fieldwork/mkosi-bind-identity` based on `1598df695abf3532af75d32796e1c7d218434293`
- Latest authoritative gate or artifact: reduced Python fixture reproducing both order-dependent collapses
- First incomplete step: execute a real `mkosi-sandbox` CLI fixture against upstream commit `f7401bdc8d23486bb346790dc92508381a062f3b`
- Cleanup state: no mounts, namespaces, files, or external systems were modified by the reduced fixture
- Next safe action: build/run the exact source in a disposable Linux environment and assert optimized operations plus observable mount/UID behavior
- External-contact state: not authorized; no upstream issue, PR, comment, email, or review created

## Intent and precedent

Current source makes `foreign` and `relative` explicit execution properties. `foreign` is parsed from `--bind-foreign` / `--ro-bind-foreign`; `relative` is parsed from a leading `+` on the source. `BindOperation.execute()` uses `relative` to select `newroot` versus `oldroot`, and the surrounding sandbox setup uses surviving bind operations' `foreign` values to decide delegated user-range setup.

History also shows `--bind-foreign` is deliberate functionality, introduced to support foreign UID ranges for directory images and virtiofsd. No open mkosi issue matching `bind foreign relative sandbox` was found during this pass.

This investigation does not infer intended duplicate precedence. It tests only the narrower invariant that operations with distinct execution semantics must not become equal merely because those semantics are absent from their identity key.

## Question

Can `FSOperation.optimize()` incorrectly discard one of two `BindOperation` instances that share source/destination/read-only/required/nofollow values but differ in `foreign` or `relative` semantics?

## Source

- Project: `systemd/mkosi`
- Requested revision: current default branch observed during this pass
- Resolved commit: `f7401bdc8d23486bb346790dc92508381a062f3b`
- Relevant file: `mkosi/sandbox.py`
- Recent adjacent mount-propagation commit inspected: `33d17b2b92b87b27842767df14c362e13023f735`
- Foreign-UID feature history inspected: `7a1754109b571657fdeeb6795eac5a55c0426d9a`
- Local source path: none; source was read through the GitHub connector
- Import metadata: none

## Environment

- Investigation host: ChatGPT tool runtime
- Runtime probe: reduced pure-Python fixture only
- Privileges: no mount or namespace privileges used
- Upstream execution: not yet run

## Baseline behavior

Current `BindOperation` identity is effectively:

```python
hash((splitpath(src), splitpath(dst), readonly, required, nofollow))
```

`foreign` and `relative` are absent. Equality is implemented as equality of the two hash values rather than equality of the underlying fields.

`FSOperation.optimize()` inserts each `BindOperation` into a dictionary before its later containment optimization. Python dictionaries retain the first equal key object when a later equal key is assigned, so the first operation's omitted semantics survive.

## Hypothesis or candidate

Hypothesis: two same-shaped binds that differ only in `foreign` or `relative` are treated as duplicates and one is discarded before execution.

A likely repair boundary, if runtime reproduction confirms the defect, is `BindOperation` identity. Any candidate should compare the actual semantic fields directly and include all behavior-changing fields used by optimization. No patch is proposed yet because end-to-end behavior has not run.

## Reproduction

Reduced fixture copied the relevant current-source logic for `splitpath`, `BindOperation.__hash__`, `BindOperation.__eq__`, and the dictionary-deduplication stage of `FSOperation.optimize()`.

```python
# same src=/src, dst=/dst, readonly=False, required=True, nofollow=False
# vary only foreign or relative, then insert through optimizer dictionary

normal_then_foreign = [bind(foreign=False), bind(foreign=True)]
foreign_then_normal = [bind(foreign=True), bind(foreign=False)]
absolute_then_relative = [bind(relative=False), bind(relative=True)]
relative_then_absolute = [bind(relative=True), bind(relative=False)]
```

Observed output:

```text
foreign normal->foreign 1 [(False, False)]
foreign foreign->normal 1 [(True, False)]
relative absolute->relative 1 [(False, False)]
relative relative->absolute 1 [(False, True)]
```

## Results

The reduced fixture produced one surviving bind in every two-operation case.

Observed:

- normal then foreign -> only normal survives;
- foreign then normal -> only foreign survives;
- absolute-source then relative-source -> only absolute semantics survive;
- relative-source then absolute-source -> only relative semantics survive.

This demonstrates that the optimizer's identity relation is order-dependent for these semantic differences.

An additional source-level correctness concern is that `__eq__()` compares only hash values. Even after adding missing fields to the hash, unrelated objects with a true hash collision would compare equal. That collision path was not brute-forced and is retained as a code-quality/invariant observation, not a reproduced practical failure.

## Interpretation

**Demonstrated behavior:** the exact current identity and dictionary-deduplication logic collapses distinct `foreign` and `relative` variants in a reduced executable fixture.

**Source-backed consequence:** the surviving `foreign` value participates in later user-range provisioning, while `relative` changes source resolution between old and new roots. Therefore the dropped distinction is execution-relevant rather than presentation-only.

**Open runtime question:** whether normal mkosi callers can or do emit duplicate-shaped pairs of these forms, and what the full CLI-visible consequence is on the exact upstream head.

## Evidence boundary

This pass did not clone or execute the complete mkosi tree, create namespaces, mount filesystems, invoke systemd-nsresourced, run the upstream test suite, or test a candidate patch. The reproduction is a reduced fixture of the exact relevant Python logic, not an authoritative end-to-end mkosi run. No claim is made about frequency in real configurations, security impact, or intended precedence when duplicate destinations are explicitly supplied.

The source identity is exact as of `f7401bdc8d23486bb346790dc92508381a062f3b`; later upstream changes may invalidate the finding.

## Next step

Run two disposable end-to-end discriminators against the exact upstream head:

1. two same-shaped binds differing only in relative-source semantics, using distinct old-root/new-root source contents so the surviving source is directly observable;
2. two same-shaped binds differing only in foreign mapping, with a synthetic owned directory and observable UID mapping outcome.

Include reversed-order controls. If the CLI reproduces order-dependent semantic loss, add focused optimizer tests and evaluate the minimal identity repair. If the CLI cannot construct or meaningfully execute these pairs, retain this as a negative/limited source-level result and document the caller invariant that makes the omission safe.

## Authority

No upstream contact is authorized or made. This record is internal Fieldwork research only.
