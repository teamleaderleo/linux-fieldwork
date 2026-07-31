# Run 999 — first independent chrootless archive difference

## Exact identity

- Linux Fieldwork PR: #361
- PR head: `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`
- generated merge: `8c2c057a9fd2b3bfc09994e009cf7957e0883691`
- workflow: `30640356619` / 999
- reproduce job: `91188432466`
- artifact: `8798679560`
- artifact digest: `sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`
- contained exit status: 6
- package tests completed: 154
- first failure: `(242/284) chrootless`

## Cleared predecessor boundary

The focused hook-free producer/consumer pair and the later broad producer both
ran before case 242. The run-974 phase-stale `tar1.txt` mismatch did not recur.
Issue #357's fixture-scope mechanism therefore cleared in real package execution.

## Exact archive delta

The failing test produced root and chrootless tarballs from the same essential
package selection and required byte identity with `cmp`.

The retained diffoscope text contains:

- 123 removed archive-listing entries;
- 123 added archive-listing entries;
- the exact same 123 paths on both sides;
- only directory entries (`drwxr-xr-x`);
- matching type, mode, uid, gid, size, and path;
- differing date/time fields only.

The root archive's differing directories all used the run epoch. The chrootless
archive retained older package directory timestamps. No regular-file entry or
content delta appeared in the diffoscope section.

## Source-supported mechanism

The tested package was mmdebstrap 1.5.7-3. Its final tar options include:

```text
--sort=name
--mtime=@$mtime
--clamp-mtime
--numeric-owner
--one-file-system
--format=pax
--pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime
```

`$mtime` is `SOURCE_DATE_EPOCH` when supplied. Clamp semantics preserve members
older than the epoch and rewrite newer members. That matches the retained
root/chrootless split.

## Claim boundary

Established:

- current sid reaches the chrootless archive comparison after 154 completed
  package tests;
- the first difference is directory-mtime-only in the retained diffoscope view;
- current clamp semantics are sufficient to explain that shape;
- run 974's phase-scoped fixture mismatch is no longer the first failure.

Not established:

- that mmdebstrap product behavior is defective rather than the comparison
  contract being too strict;
- that all four include variants fail identically, because `--exitfirst` stopped
  at the first archive comparison;
- that changing directory mtimes is harmless across every output format;
- any upstream frequency, impact, or accepted policy.

## Routing

Issue #380 owns the focused policy comparison. PR #361 remains the exact package
execution carrier. No further full sid run is justified until the focused matrix
selects a bounded candidate.
