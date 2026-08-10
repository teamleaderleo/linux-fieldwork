# mkosi sandbox bind-operation identity drops behavior-changing flags

## TL;DR

At `systemd/mkosi` commit `f7401bdc8d23486bb346790dc92508381a062f3b`, `BindOperation.__hash__()` omits the behavior-changing `foreign` and `relative` fields, while `__eq__()` defines equality as equal hashes. `FSOperation.optimize()` first inserts bind operations into a dictionary, so two otherwise identical binds that differ only in either omitted field collapse to one operation and the first operation's semantics survive.

A second optimizer path is also affected: the nested-bind redundancy check compares `readonly`, `required`, `relative`, and `nofollow`, but not `foreign`. A foreign parent plus normal child, or normal parent plus foreign child, is therefore reduced to only the parent when source/destination subpaths line up, even though the child has different idmapping semantics.

Reduced execution of the exact identity/optimizer logic reproduces both classes. History makes the `relative` defect especially strong: the commit that introduced `+SRC` explicitly changed containment and sorting to preserve relative-vs-host-root semantics, but did not add `relative` to bind identity. A minimal candidate that compares all semantic identity fields directly and adds `foreign` to the containment discriminator passes the reduced negative controls. Full `mkosi-sandbox` runtime execution remains outstanding because this tool runtime cannot resolve GitHub for a local clone.

## Explain like I'm five

The sandbox builds a list of mounts and removes ones it thinks are duplicates or redundant. Some mounts look almost identical but mean different things: one can read its source from inside the sandbox instead of the host, and one can remap a special UID range. Those choices are missing from parts of the optimizer's idea of “same”.

Literal examples:

- `normal bind /src -> /dst` followed by `foreign bind /src -> /dst` enters the optimizer; the reduced fixture returns only the first normal bind. Reversing the order returns only the foreign bind.
- `foreign bind /src -> /dst` plus `normal bind /src/sub -> /dst/sub` enters the nested redundancy pass; the child override is discarded and only the foreign parent survives.

## Why care

The affected code is `mkosi/sandbox.py`. `foreign` controls whether a bind is prepared through a transient user namespace and `systemd-mountfsd`; `relative` changes whether source lookup begins at the sandbox root or host root. Losing either distinction can therefore change which object is mounted or whether its IDs are mapped.

The foreign path is not dead code: it was added for directory-image/QEMU/virtiofsd handling and is documented as requiring `systemd-nsresourced` plus `systemd-mountfsd` v260 or newer.

## Current state

- State: `EXECUTING`
- Exact working head before this update: fieldwork commit `affb77ef500c9754629e43c1e225294741f8704c`
- Latest authoritative gate: exact-logic reduced fixture reproduces duplicate collapse and nested foreign/normal collapse; repaired reduced fixture preserves semantic variants while still removing genuinely redundant same-semantics children
- First incomplete step: execute the real `mkosi-sandbox` CLI against upstream commit `f7401bdc8d23486bb346790dc92508381a062f3b`
- Cleanup state: clean; no mounts, namespaces, files, or external systems modified by the reduced probes
- Next safe action: run disposable upstream CLI fixtures when an execution environment with source/network is available; if confirmed, materialize focused upstream-style tests and a one-file candidate
- External-contact state: not authorized; no upstream issue, PR, comment, email, or review created

## Intent and precedent

### Relative-source history

Commit `204d2a5136cad09d01aefe62e4b9bf51ac84c705` (`sandbox: Allow taking bind source paths relative to the sandbox root`) introduced the leading-`+` source convention. That change:

- added `relative` as an operation field;
- changed source resolution to use `newroot` instead of `oldroot` when relative;
- added `m.relative == n.relative` to nested-bind elimination;
- changed sorting so relative operations always go last.

It did **not** add `relative` to `BindOperation.__hash__()`. Because dictionary deduplication runs before the containment/sort logic, identical path/flag pairs that differ only in `relative` can collapse before the newly added relative-aware rules are reached. This is direct intent evidence that `relative` was meant to remain a distinguishing optimizer property.

### Foreign-UID history

Commit `7a1754109b571657fdeeb6795eac5a55c0426d9a` added `foreign`, `mappedfd`, `--bind-foreign`, and the systemd user-range/mountfsd machinery. The commit leaves the existing bind hash untouched, and the current nested elimination predicate still has no `foreign` discriminator.

The feature's own history states that QEMU directory-image handling uses `--bind-foreign` so virtiofsd sees an idmapped foreign UID range. That makes `foreign` an execution property, not annotation.

No matching open mkosi issue was found during the initial pass.

## Question

Can `FSOperation.optimize()` incorrectly discard `BindOperation` instances whose path shape is otherwise redundant but whose `foreign` or `relative` semantics differ?

## Source

- Project: `systemd/mkosi`
- Requested revision: current default branch observed during this pass
- Resolved commit: `f7401bdc8d23486bb346790dc92508381a062f3b`
- Relevant file: `mkosi/sandbox.py`
- Relative-source introduction: `204d2a5136cad09d01aefe62e4b9bf51ac84c705`
- Foreign-UID feature introduction: `7a1754109b571657fdeeb6795eac5a55c0426d9a`
- Recent adjacent mount-propagation change inspected: `33d17b2b92b87b27842767df14c362e13023f735`
- Local source path: none; exact source was read through the GitHub connector
- Import metadata: none

## Environment

- Investigation host: ChatGPT tool runtime
- Runtime probes: reduced pure-Python fixtures of exact relevant source logic
- Privileges: no mount or namespace privileges used
- Local clone attempt: failed before source retrieval because the container could not resolve `github.com`; classified as tooling/network interruption, not product behavior
- Upstream runtime execution: not yet run

## Baseline behavior

Current bind identity is effectively:

```python
hash((splitpath(src), splitpath(dst), readonly, required, nofollow))
```

`foreign` and `relative` are absent. Equality is implemented as equality of the two hash values rather than equality of the underlying fields.

`FSOperation.optimize()` then performs two relevant stages:

1. inserts each bind into a dictionary, collapsing equal keys before later logic;
2. drops a nested bind when source and destination relative paths match and selected flags match.

The second stage checks `readonly`, `required`, `relative`, and `nofollow`, but not `foreign`.

## Reproduction

### Duplicate-shaped semantic variants

Reduced fixture copied the current-source logic for `splitpath`, `BindOperation.__hash__`, `BindOperation.__eq__`, dictionary deduplication, and optimizer sorting.

```text
foreign normal->foreign 1 [(False, False)]
foreign foreign->normal 1 [(True, False)]
relative absolute->relative 1 [(False, False)]
relative relative->absolute 1 [(False, True)]
```

Observed:

- normal then foreign -> only normal survives;
- foreign then normal -> only foreign survives;
- absolute-source then relative-source -> only absolute semantics survive;
- relative-source then absolute-source -> only relative semantics survive.

### Nested foreign/normal variants

Using the exact current nested-elimination predicate:

```text
outer foreign /src->/dst + inner normal /src/sub->/dst/sub
=> [outer foreign]

outer normal /src->/dst + inner foreign /src/sub->/dst/sub
=> [outer normal]
```

In both directions the child operation is classified as redundant despite carrying different idmapping semantics.

### Candidate reduced fixture

A minimal candidate model was tested with these changes:

- identity key includes `foreign` and `relative`;
- equality compares the complete semantic key directly rather than comparing hash values;
- nested redundancy requires `m.foreign == n.foreign`.

The candidate reduced fixture produced:

```text
same path normal + foreign => both survive
same path absolute + relative => both survive
foreign parent + normal child => both survive
normal parent + foreign child => both survive
same-semantics parent + child => child still removed as redundant
```

This is a negative control for over-fixing: the optimizer still removes a truly redundant nested bind when semantics match.

## Candidate boundary

If end-to-end execution confirms the source/reduced-fixture result, the smallest repair appears to be entirely inside `mkosi/sandbox.py`:

```python
def _key(self):
    return (
        splitpath(self.src),
        splitpath(self.dst),
        self.readonly,
        self.required,
        self.foreign,
        self.relative,
        self.nofollow,
    )

def __hash__(self) -> int:
    return hash(self._key())

def __eq__(self, other: object) -> bool:
    return isinstance(other, BindOperation) and self._key() == other._key()
```

and add `m.foreign == n.foreign` to the nested-bind redundancy predicate.

This is a design sketch, not yet a validated upstream patch. `mappedfd` should remain outside identity because it is acquired execution state rather than requested semantics.

## Interpretation

**Demonstrated:** the current optimizer's first-stage identity collapses exact-path bind variants that differ only in `foreign` or `relative` in a reduced execution of the exact logic.

**Demonstrated:** its second-stage containment rule removes nested bind variants that differ only in `foreign`.

**Intent-backed:** `relative` was explicitly added to containment and ordering when introduced, but omitted from identity, so the first-stage collapse bypasses the relative-aware behavior introduced in the same change.

**Source-backed consequence:** `relative` selects old-root versus new-root source resolution; `foreign` selects idmapped mount preparation and influences user-range setup.

**Open runtime question:** the exact CLI-visible outcome on a real sandbox for deliberately overlapping semantic variants, and whether normal high-level mkosi callers currently generate such combinations without explicit user options.

## Evidence boundary

This pass did not execute complete mkosi, create namespaces, mount filesystems, invoke `systemd-nsresourced`/`systemd-mountfsd`, run the upstream suite, or validate a candidate against real source. The local clone attempt failed at DNS resolution before any source could be retrieved and is recorded only as a tooling interruption.

No claim is made about frequency in real configurations, security impact, or intended precedence for arbitrary user-supplied duplicate destinations beyond the relative-order intent visible in history. The source identity is exact as of `f7401bdc8d23486bb346790dc92508381a062f3b`.

## Next step

Run three disposable end-to-end discriminators against the exact upstream head:

1. same path pair differing only in relative-source semantics, with distinct host-root/sandbox-root bytes and reversed order;
2. same path pair differing only in foreign mapping, with a synthetic directory and observable UID mapping outcome;
3. parent/child bind pair with opposite foreign semantics, proving whether the child override is lost after optimization.

Then add focused optimizer unit coverage for both semantic axes and validate the minimal identity/containment repair. Keep the true-redundancy negative control.

## Authority

No upstream contact is authorized or made. This record is internal Fieldwork research only.
