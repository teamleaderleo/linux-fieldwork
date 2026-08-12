# squashfs-tools v2/v3 fragment hardening leaves index==count out of bounds

Date: 2026-08-12

## TL;DR

Current `unsquash-2.c` and `unsquash-3.c` contain a new August 2026 corruption check intended to reject inode fragment indexes beyond the fragment table, but the comparison is off by one:

```c
if(fragment > sBlk.s.fragments)
    EXIT_UNSQUASH(...);
fragment_entry = &fragment_table[fragment];
```

`sBlk.s.fragments` is the **number of entries**, not the maximum valid index. Both readers allocate the table for exactly `sBlk.s.fragments` fragment entries and loop over entries with `i < sBlk.s.fragments`. Therefore `fragment == sBlk.s.fragments` passes the new check and indexes exactly one entry past the allocation.

The current v4 reader already uses the correct boundary:

```c
if(fragment >= sBlk.s.fragments)
    EXIT_UNSQUASH(...);
```

The incorrect v2/v3 checks were added on August 3, 2026 by commits explicitly titled “check for corrupted inode fragment index,” so this is an incomplete hardening fix rather than an old undocumented assumption.

No upstream contact is authorized or has been made.

## Exact source boundary

Project: `plougher/squashfs-tools`

Reviewed head:

`5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491`

Relevant files:

- `squashfs-tools/unsquash-2.c`
- `squashfs-tools/unsquash-3.c`
- passing control: `squashfs-tools/unsquash-4.c`

Hardening commits:

- `a5d6d84a25a09363a73dcec86a9e51ce81f99e01` — `Unsquash-2: check for corrupted inode fragment index`
- `4d20c07359a2b49c19793cd5c79bc683b8a9d255` — `Unsquash-3: check for corrupted inode fragment index`

Both were committed August 3, 2026.

## Allocation/count proof in v2

`read_fragment_table()` computes:

```c
long long bytes = SQUASHFS_FRAGMENT_BYTES_2((long long) sBlk.s.fragments);
...
fragment_table = MALLOC(bytes);
```

and, when byte-swapping entries, iterates:

```c
for(i = 0; i < sBlk.s.fragments; i++) {
    ... fragment_table[i] ...
}
```

The fragment count therefore describes exactly the number of table entries.

`read_fragment()` currently rejects only:

```c
fragment > sBlk.s.fragments
```

then performs:

```c
fragment_table[fragment]
```

For `sBlk.s.fragments == 1`, only index 0 is allocated/valid. A corrupted inode fragment value 1 is accepted by the check and selects `fragment_table[1]`.

The v3 implementation has the same count loop and same `>` check.

## v4 passing control

Current `unsquash-4.c::read_fragment()` uses:

```c
if(fragment >= sBlk.s.fragments)
    EXIT_UNSQUASH(...);
```

This is strong in-tree confirmation of the intended table-count semantics, not an inference based only on C allocation convention.

## Candidate

Tracked `candidate.patch` changes the two comparisons from `>` to `>=`.

No format/wire behavior changes for valid images: indexes `0 .. fragments-1` continue to be accepted; only the first invalid index is rejected.

## Reduced discriminator

Tracked `repro.c` models the exact count boundary without deliberately performing an invalid memory access:

```text
count = 1
fragment = 1
current check: accepted
candidate check: rejected
valid indexes: [0]
```

The exact current source dereferences the accepted index immediately afterward; the allocation/count proof establishes why that dereference is outside the table.

A future owned integration can mutate a v2/v3 inode fragment field to equal the superblock fragment count and run the exact reviewed `unsquashfs` under ASan. That stronger executable discriminator is not required to establish the comparison defect.

## Upstream policy boundary

Current `SECURITY.md` says security issues should be opened publicly on the project's GitHub issue tracker and should not be sent privately to maintainer email addresses.

Fieldwork has **not** contacted upstream. The policy is recorded only to avoid accidentally routing any later explicitly authorized report through a channel the project rejects.

## Duplicate search

Open and closed upstream issue searches for fragment-index/off-by-one/v2/v3 wording returned no matching report during this pass.

## Evidence boundary

Demonstrated:

- exact current v2 and v3 source uses `>` then indexes the fragment table;
- fragment table allocation/count loops show `sBlk.s.fragments` is an entry count;
- v4 uses the correct `>=` boundary;
- the incorrect comparisons were introduced by the August 3 hardening commits themselves;
- a two-line candidate repairs only the first invalid index;
- no matching upstream issue was found.

Not yet demonstrated:

- an exact-head ASan run against a crafted v2/v3 image;
- whether a particular out-of-bounds read reliably crashes versus only reading adjacent allocation data;
- any security impact beyond malformed-image robustness. This investigation does not make an exploitability claim.

## Cleanup

The reduced fixture is pure process-local control flow. No archive, mount, namespace, or persistent state was created.

## Current disposition

State: `EXECUTING`

Next safe actions:

1. build an owned minimal v2/v3 mutation fixture if convenient;
2. inspect sibling August corruption checks for the same `>` versus `>=` transcription error;
3. audit other legacy reader tables where counts are checked against indexes.

External-contact state: no upstream interaction authorized or made.
