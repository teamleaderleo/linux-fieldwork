# libblkid Minix v3 cross-endian magic is advertised but rejected

## TL;DR

At util-linux master commit `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`, libblkid's Minix probe advertises both little-endian and big-endian Minix v3 magic byte sequences, but `get_minix_version()` only recognizes the v3 magic in native byte order. In its explicit “other endian” retry, v1/v2 magic is byte-swapped while the v3 comparison repeats the unswapped expression.

A reduced executable copy of the exact version classifier on a little-endian host produces the distinguishing matrix:

```text
v1 LE -> version 1, native
v1 BE -> version 1, other endian
v3 LE -> version 3, native
v3 BE -> rejected
```

Changing only the second v3 comparison to `swab16(sb3->s_magic) == MINIX3_SUPER_MAGIC` makes the BE v3 cell return version 3 with `other_endian=1` while preserving all three controls. This aligns with the rest of `probe_minix()`, which already byte-swaps the v3 numeric fields when `swabme` is set.

The source history supports this as a real compatibility intention rather than a decorative magic-table entry: util-linux has maintained mkfs/fsck Minix v3 behavior on big-endian systems and previously fixed v2/v3 big-endian bugs in that path. Full libblkid execution against a real opposite-endian Minix v3 image remains the next authoritative gate.

## Explain like I'm five

A filesystem writes a two-byte ID number into its superblock. On a machine with the opposite byte order, those two bytes appear reversed.

libblkid knows how to try both byte orders. It does that correctly for Minix versions 1 and 2. For version 3 it has an entry saying “also try the reversed bytes,” but when the deeper check runs it forgets to reverse them. The probe enters the right door and then gets turned away by the second guard.

## Why care

libblkid is used by `blkid`, udev and other storage discovery paths. A valid Minix v3 filesystem created in the opposite byte order can reach the Minix probe through the advertised magic but fail classification at `get_minix_version()`.

This is a portability/correctness defect, not a security claim. The practical reach depends on whether a filesystem created on one-endian hardware is probed on the other, or an image is moved between architectures.

## Current state

- State: `EXECUTING`
- util-linux exact source head: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Relevant file: `libblkid/src/superblocks/minix.c`
- Latest authoritative Fieldwork gate: reduced exact classifier with v1/v3 native/other-endian matrix and one-line candidate discriminator
- First incomplete step: run real libblkid low-probe against a structurally valid opposite-endian Minix v3 image
- Cleanup state: no devices, images, mounts, or external systems modified
- Next safe action: retain executable reduced probe, then build/generate or import a valid cross-endian v3 fixture and compare baseline/candidate libblkid
- External-contact state: not authorized; no upstream issue, PR, comment, review, or email created

## Intent and precedent

### Current magic table

`minix_idinfo.magics` contains:

```text
v1 LE and BE
v2 LE and BE
v3 LE: 5a 4d
v3 BE: 4d 5a
```

So the probe's declared source-selection surface explicitly accepts both byte sequences.

### Current classifier

`get_minix_version()` first checks native-order v1/v2 magic and then:

```c
if (sb3->s_magic == MINIX3_SUPER_MAGIC)
        version = 3;
```

If nothing matched, it sets `*other_endian = 1`, correctly uses `swab16(sb->s_magic)` for v1/v2, but its v3 fallback is again:

```c
if (sb3->s_magic == MINIX3_SUPER_MAGIC)
        version = 3;
```

The same unswapped comparison cannot distinguish the opposite-endian v3 magic that caused the fallback.

### Downstream field handling is already endian-aware

When version 3 is returned, `probe_minix()` reads:

- `s_zones` with `minix_swab32(swabme, ...)`;
- `s_ninodes` with `minix_swab32(swabme, ...)`;
- bitmap counts, first data zone and block size with `minix_swab16(swabme, ...)`.

So recognizing an other-endian v3 superblock does not require a broader data-model change; the field path already consumes `swabme`.

### Big-endian project history

util-linux commit `7252874a48e3cc7382d579254a19fc4c309442c1` is explicitly titled `mkfs.minix: fix v2/v3 .badblocks inode number for big endian` and states that the Minix v2/v3 creation path is exercised on big-endian systems.

The 2016 Minix test/fix series merged in `fdbfe2e7f0dd4918f1b690e857d319045c2dfd34` includes `tests: fix minix tests for big endian` and several v3 corrections. This is useful intent evidence that v3 endian portability is a maintained behavior in the project rather than an unsupported synthetic case.

Linux's current Minix filesystem implementation itself reads the on-disk fields in native order and does not provide cross-endian mounting. That narrows the libblkid value proposition: detection of moved/cross-architecture images is independent of whether the current kernel can mount such an image directly. libblkid already makes that portability choice for Minix v1/v2 and advertises the v3 BE magic too.

## Question

Does the current Minix probe fail to classify an otherwise valid Minix v3 superblock when its on-disk byte order differs from the probing host, despite advertising that opposite-endian magic and already having v3 swab-aware field parsing?

## Source

- Project: `util-linux/util-linux`
- Requested revision: current `master` during this pass
- Resolved commit: `ce6a4ea30e0f6b46b9689931cab897c6bd866bd6`
- Relevant source: `libblkid/src/superblocks/minix.c`, `include/minix.h`
- Adjacent recent seed: `cf479ca5f61d5342d1c66952161136efbd183911` (`libblkid: minix: don't detect erofs images as minix`)
- Big-endian precedent: `7252874a48e3cc7382d579254a19fc4c309442c1`, merge `fdbfe2e7f0dd4918f1b690e857d319045c2dfd34`
- Linux reference source read: `torvalds/linux` commit `d58772d8520c7ef247c4b95c9bd76d3a25da9ff5`, `fs/minix/inode.c`
- Local upstream source path: none; exact sources read through GitHub connector

## Baseline behavior

On a little-endian host, the byte-level version classifier is expected to see:

```text
v1 LE magic bytes: 7f 13
v1 BE magic bytes: 13 7f
v3 LE magic bytes: 5a 4d
v3 BE magic bytes: 4d 5a
```

The current logic recognizes the first three combinations but rejects the fourth after setting `other_endian=1`.

The important negative control is v1 BE: it proves the fixture is exercising the intended existing cross-endian branch rather than merely injecting an unknown byte sequence.

## Reproduction

A reduced pure-Python fixture copies only the exact current byte-order decision from `get_minix_version()` and uses the real v1/v3 magic offsets:

```text
current v1 LE -> (1, other_endian=0)
current v1 BE -> (1, other_endian=1)
current v3 LE -> (3, other_endian=0)
current v3 BE -> (-1, other_endian=1)
```

The candidate changes only the other-endian v3 comparison:

```c
if (swab16(sb3->s_magic) == MINIX3_SUPER_MAGIC)
        version = 3;
```

Candidate reduced result:

```text
candidate v1 LE -> (1, 0)
candidate v1 BE -> (1, 1)
candidate v3 LE -> (3, 0)
candidate v3 BE -> (3, 1)
```

No other classifier cell changes.

## Candidate boundary

The source-level repair is one expression inside the existing opposite-endian fallback:

```diff
 default:
-	if (sb3->s_magic == MINIX3_SUPER_MAGIC)
+	if (swab16(sb3->s_magic) == MINIX3_SUPER_MAGIC)
 		version = 3;
 	break;
```

A real candidate should also add a libblkid fixture that proves opposite-endian v3 classification, not rely only on the reduced helper.

No change is proposed to Minix v1/v2, the magic table, Minix structural sanity checks, or kernel mount behavior.

## Cross-context checks

### Native v3

The first/native comparison remains unchanged, so native-endian v3 continues through `swabme=0`.

### Other-endian v1/v2

Their existing `swab16()` comparisons are the control and remain unchanged.

### V3 field decoding

Every v3 field used by the probe already passes through `minix_swab16/32(swabme, ...)`, so the candidate does not introduce an unswapped-field donut after fixing magic recognition.

### Magic selection versus semantic validation

The outer `blkid_idmag` list already contains the BE v3 bytes. The defect is therefore after selector match and before structural validation, not a missing selector.

### Linux mount support

Current Linux Minix mount code does not appear to byte-swap an opposite-endian image. The Fieldwork claim is limited to libblkid classification consistency and portability, not mountability on the probing kernel.

## Interpretation

**Demonstrated source behavior:** the other-endian v3 branch repeats the native comparison and cannot return v3 for swapped magic.

**Demonstrated reduced behavior:** the exact four-cell classifier matrix rejects only BE v3 on a little-endian model; a one-expression swab repair makes it match while preserving controls.

**Intent evidence:** the magic table advertises both v3 byte orders, downstream v3 fields honor `swabme`, and util-linux history contains explicit Minix v3 big-endian fixes/tests.

**Open authoritative runtime question:** whether a complete structurally valid v3 image made on one endian is accepted by patched libblkid on the other, including all sanity checks and reported endianness metadata.

## Evidence boundary

No complete Minix filesystem image was generated in this pass and libblkid itself was not executed. The current result is exact source/history plus a reduced executable discriminator.

This investigation does not claim cross-endian Minix v3 can be mounted by the Linux kernel. It also does not claim common deployment frequency. No security impact is asserted.

The reduced fixture assumes a little-endian probing host for concreteness; the defect is symmetric in concept because the fallback should represent “other endian,” but an actual big-endian runtime remains unexecuted.

## Next step

1. retain the reduced probe as a durable artifact;
2. obtain or generate a structurally valid Minix v3 opposite-endian image without modifying a real device;
3. run current `blkid -p` / the focused libblkid test and capture baseline failure;
4. apply the one-expression candidate and rerun the identical image;
5. assert `TYPE=minix`, version `3`, endianness metadata, block size, and no ambiguity;
6. keep native v1/v2/v3 plus other-endian v1/v2 as controls;
7. clean the disposable image and rerun the focused test.

If a valid opposite-endian image reveals a separate structural-field or sanity-check incompatibility, split that as a new owner instead of widening this magic fix silently.

## Authority

No upstream issue, pull request, comment, review, email, or other interaction was created. Upstream contact remains unauthorized.
