# Current runtime results — libblkid Minix cross-endian v3

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#570`

## TL;DR

The Minix v3 cross-endian defect now reproduces through a complete installed libblkid probe, not only the reduced version classifier.

On the current execution host, `blkid` reports libblkid/util-linux 2.41. A four-cell synthetic superblock matrix with identical logical geometry gives:

```text
Minix v1 little-endian -> detected, VERSION=1, ENDIANNESS=LITTLE
Minix v1 big-endian    -> detected, VERSION=1, ENDIANNESS=BIG
Minix v3 little-endian -> detected, VERSION=3, ENDIANNESS=LITTLE
Minix v3 big-endian    -> unrecognized, blkid probe rc=2
```

This is a strong differential because opposite-endian Minix itself is demonstrably supported by the same libblkid build for v1. The losing cell is specifically v3 opposite-endian.

Current util-linux `main` at `53e442154c97b872b529a9f61e335d150ad0f742` still contains the source asymmetry:

```c
/* v1/v2 other-endian fallback */
switch (swab16(sb->s_magic)) {
    ...
    default:
        if (sb3->s_magic == MINIX3_SUPER_MAGIC)
            version = 3;
}
```

The outer Minix magic table still advertises both v3 byte orders, and the v3 field/sanity path already applies `swabme` to its multi-byte fields. The owned source candidate changes only that v3 fallback comparison to `swab16(sb3->s_magic)`.

## Explain like I'm five

libblkid knows how to read Minix filesystems written in the other byte order.

The same test program correctly recognizes a big-endian Minix v1 superblock on this little-endian machine. For Minix v3, the outer magic scanner also recognizes the big-endian magic, but the next function forgets to swap those two magic bytes before comparing them. The probe stops there.

## Why care

This closes the main runtime uncertainty from the earlier scout. The result is no longer only “the C expression looks inconsistent.” A real libblkid build accepts the native and v1 cross-endian controls while rejecting exactly the v3 cross-endian fixture predicted by the source defect.

The claim remains about libblkid identification/portability. It does not claim that the running Linux kernel can mount an opposite-endian Minix v3 filesystem.

## Exact source boundary

- Current util-linux upstream head reviewed: `53e442154c97b872b529a9f61e335d150ad0f742`
- Current `libblkid/src/superblocks/minix.c` blob: `85affee23d98695ef2560eea55eee54838d19bbb`
- Current `include/minix.h` blob: `571d06e8d0e8b63ae7142a20681fbf64daf42f34`
- Installed runtime probe: `blkid from util-linux 2.41 (libblkid 2.41.0, 18-Mar-2025)`
- Architecture: x86_64 little-endian execution environment
- Privileges: ordinary file probes; no mounts or loop devices

## Synthetic fixture

Each image is an 8192-byte zero-filled regular file with one packed Minix superblock at byte offset 1024. The geometry is deliberately small but satisfies the exact sanity constraints used by `probe_minix()`.

### v1 logical values

```text
ninodes       = 16
nzones        = 100
imap_blocks   = 1
zmap_blocks   = 1
firstdatazone = 5
log_zone_size = 0
max_size      = 0x7fffffff
magic         = 0x137f
state         = MINIX_VALID_FS (1)
zones         = 100
```

### v3 logical values

```text
ninodes       = 16
pad0          = 0
imap_blocks   = 1
zmap_blocks   = 1
firstdatazone = 5
log_zone_size = 0
pad1          = 0
max_size      = 0x7fffffff
zones         = 100
magic         = 0x4d5a
pad2          = 0
blocksize     = 1024
disk_version  = 3
```

The only difference between each LE/BE pair is the byte order used to encode multi-byte fields.

Generator:

```python
import struct

v1 = (16, 100, 1, 1, 5, 0, 0x7fffffff, 0x137f, 1, 100)
for name, fmt in [
    ("minix1-le.img", "<HHHHHHIHHI"),
    ("minix1-be.img", ">HHHHHHIHHI"),
]:
    data = bytearray(8192)
    sb = struct.pack(fmt, *v1)
    data[1024:1024 + len(sb)] = sb
    open(name, "wb").write(data)

v3 = (16, 0, 1, 1, 5, 0, 0, 0x7fffffff, 100, 0x4d5a, 0, 1024, 3)
for name, fmt in [
    ("minix3-le.img", "<IHHHHHHIIHHHB"),
    ("minix3-be.img", ">IHHHHHHIIHHHB"),
]:
    data = bytearray(8192)
    sb = struct.pack(fmt, *v3)
    data[1024:1024 + len(sb)] = sb
    open(name, "wb").write(data)
```

Probe command:

```sh
blkid -p -o export IMAGE
```

## Observed results

### v1 little-endian

```text
VERSION=1
FSBLOCKSIZE=1024
BLOCK_SIZE=1024
ENDIANNESS=LITTLE
TYPE=minix
USAGE=filesystem
rc=0
```

### v1 big-endian

```text
VERSION=1
FSBLOCKSIZE=1024
BLOCK_SIZE=1024
ENDIANNESS=BIG
TYPE=minix
USAGE=filesystem
rc=0
```

### v3 little-endian

```text
VERSION=3
FSBLOCKSIZE=1024
BLOCK_SIZE=1024
ENDIANNESS=LITTLE
TYPE=minix
USAGE=filesystem
rc=0
```

### v3 big-endian

```text
(no probe fields)
rc=2
```

## Source interpretation

The runtime matrix matches the current source path exactly.

For v1/v2, the fallback switches on `swab16(sb->s_magic)`, sets `other_endian`, and later decodes geometry with `minix_swab16/32(swabme, ...)`.

For v3, the fallback currently repeats the native comparison:

```c
if (sb3->s_magic == MINIX3_SUPER_MAGIC)
```

so the BE v3 fixture never reaches the already-swab-aware v3 geometry path.

The candidate is:

```diff
- if (sb3->s_magic == MINIX3_SUPER_MAGIC)
+ if (swab16(sb3->s_magic) == MINIX3_SUPER_MAGIC)
```

That change is restricted to the other-endian fallback branch.

## Owned source candidate

- Repository: `teamleaderleo/util-linux`
- Branch: `linux-fieldwork/libblkid-minix3-endian`
- Exact base: `53e442154c97b872b529a9f61e335d150ad0f742`
- Candidate head: `eebfe13d1dd1c15dc66976723f1e3d001f6fc121`
- Semantic product change: one comparison in `libblkid/src/superblocks/minix.c`

Carrier self-review found one non-semantic artifact from the whole-file connector write: the commit also removes the file's final blank line. Treat this head as retained evidence, not presentation-ready source history. Rebuild the candidate cleanly before human review/upstream packaging.

No sign-off identity was inferred or synthesized.

## Evidence boundary

Demonstrated:

- full installed libblkid detection of native v1, opposite-endian v1, and native v3 synthetic superblocks;
- full installed libblkid rejection of the logically corresponding opposite-endian v3 superblock;
- current util-linux main still has the exact classifier asymmetry;
- current v3 geometry decoding is already `swabme`-aware;
- current magic table advertises both v3 byte orders;
- owned current-base source candidate changes the losing magic comparison.

Pending:

- compile current util-linux/libblkid with the candidate;
- rerun the same four images against that exact candidate build;
- run focused libblkid tests and broader relevant validation;
- rebuild a clean one-commit source carrier without the trailing-blank-line artifact;
- prepare DCO/sign-off only if a human later chooses an upstream submission path.

## Cleanup

Only four regular files under `/tmp` were created. No devices, mounts, namespaces, filesystem writes outside the disposable files, or external systems were touched.

## Current disposition

- State: `REPAIR / RUNTIME-REPRODUCED`
- Current source defect: survives `53e442154...`
- Full-probe differential: reproduced on libblkid 2.41
- Passing cross-endian control: Minix v1 BE
- Losing cell: Minix v3 BE only
- Candidate semantic hunk: one `swab16()`
- Next safe action: build exact-current libblkid candidate and rerun the identical four-cell fixture before promotion
- External-contact state: no upstream comment, issue, PR, review, reaction, email, or patch submission authorized or made
