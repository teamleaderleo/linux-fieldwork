# squashfs-tools v2/v3 fragment hardening leaves index==count out of bounds

Date: 2026-08-12

## TL;DR

Exact-current `plougher/squashfs-tools` was reproduced under ASan/UBSan with real legacy SquashFS images.

At upstream head:

`5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491`

both `unsquash-2.c` and `unsquash-3.c` accept an inode fragment index equal to the fragment count and then index one entry past the allocated fragment table. ASan reports a heap-buffer-overflow in `read_fragment()` for both readers.

`sBlk.s.fragments` is an entry count. Valid fragment indexes are therefore `0 .. sBlk.s.fragments - 1`. The current v4 reader already enforces that boundary with `>=`.

The minimal candidate remains exactly two comparison changes:

```diff
- if(fragment > sBlk.s.fragments)
+ if(fragment >= sBlk.s.fragments)
```

at the v2 and v3 `read_fragment()` sites. With that candidate, `count - 1` still extracts successfully, `count` and `count + 1` are rejected as corrupt input before the table access, and zero-fragment images still extract successfully.

Observed impact: **out-of-bounds read on malformed filesystem input**. No exploitability claim is made.

No upstream contact is authorized or has been made.

## Exact heads

Execution target and final source refresh:

- Fieldwork main at clean-candidate branch point: `53e369c8382f9e184aa781447ca3a233ff1f3ab7`
- `plougher/squashfs-tools` master, tested and refreshed after execution: `5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491`

Relevant upstream files:

- `squashfs-tools/unsquash-2.c`
- `squashfs-tools/unsquash-3.c`
- passing semantic control: `squashfs-tools/unsquash-4.c`

## Count and index semantics

### v2

`read_fragment_table()` computes the table byte count from `sBlk.s.fragments`, allocates exactly that many entries, and iterates entries with `i < sBlk.s.fragments`.

The reader then uses:

```c
if(fragment > sBlk.s.fragments)
    EXIT_UNSQUASH(...);

fragment_entry = &fragment_table[fragment];
```

For `sBlk.s.fragments == 1`, the allocation contains one entry, index `0`. A malformed inode fragment value `1` passes the check and indexes `fragment_table[1]`.

### v3

The v3 fragment-table allocation and iteration use the same count semantics, and its `read_fragment()` has the same `>` guard followed by `fragment_table[fragment]`.

### v4 control

Current v4 uses the expected count boundary:

```c
if(fragment >= sBlk.s.fragments)
    EXIT_UNSQUASH(...);
```

This confirms the intended zero-based table-index semantics in the current reader family.

## Candidate history

The legacy guards were added in the August 3, 2026 hardening series:

- `a5d6d84a25a09363a73dcec86a9e51ce81f99e01` — `Unsquash-2: check for corrupted inode fragment index`
- `4d20c07359a2b49c19793cd5c79bc683b8a9d255` — `Unsquash-3: check for corrupted inode fragment index`

Each introduced `fragment > sBlk.s.fragments` before the table dereference.

The earlier v4 hardening commit:

- `f3783bbec5b0f105c6571699d3fd38803a345b12`

uses `fragment >= sBlk.s.fragments`.

A fresh upstream issue/PR overlap search found adjacent fragment bugs but no matching report for the `fragment == fragment_count` boundary. A separate Fieldwork review split unrelated arithmetic findings into #632 and #633 instead of widening this investigation.

## Exact-current sanitizer build

Both successful parser runs built the exact reviewed head on Ubuntu 24.04 with GCC 13.3.0 using the normal supported compressor set:

```sh
git clone https://github.com/plougher/squashfs-tools.git /tmp/sq
cd /tmp/sq
git checkout --detach 5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491

test "$(git rev-parse HEAD)" = \
  5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491

make -C squashfs-tools clean
make -C squashfs-tools \
  EXTRA_CFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
  EXTRA_LDFLAGS='-fsanitize=address,undefined' \
  unsquashfs
```

Runtime sanitizer settings:

```sh
export ASAN_OPTIONS='halt_on_error=1:abort_on_error=1:detect_leaks=0'
export UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'
```

Each parser case used one worker to keep the trace deterministic:

```sh
./unsquashfs -processors 1 -no-progress -d DEST IMAGE
```

## Real v2 reproducer

### Generator provenance

The fixture generator came from the official SquashFS `squashfs2.2-r2.tar.gz` release archive.

Downloaded tarball SHA-256:

```text
750a7a4896d782698a0f531ca30582f0ddd365fe317a04c4dd4fa1ce2eb053eb
```

The built generator reports:

```text
mksquashfs version 2.2-r2
```

The generated image is a valid little-endian SquashFS `2:1` filesystem according to exact-current `unsquashfs -s`.

The historical source needs only compiler-compatibility flags on the current runner:

```sh
OLD_CFLAGS='-I. -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_GNU_SOURCE -O2 -fcommon -include sys/sysmacros.h'
make CFLAGS="$OLD_CFLAGS" mksquashfs
```

### Base image

Input tree:

```sh
mkdir /tmp/src-v2
printf Z > /tmp/src-v2/file
./mksquashfs /tmp/src-v2 v2-base.sqfs -noI -noD -noF -nopad
```

The generator reports one fragment. A tiny helper compiled against the historical `squashfs_fs.h` produced the real field layout:

```text
fragments=55 fragments_size=4
inode_table_start=20 inode_table_start_size=4
reg_size=24 reg_fragment=12 file_type=2
```

Derived fixture details:

```text
fragment_count              = 1
inode_table_start           = 64
inode metadata header       = 0x8027  (uncompressed)
regular-inode fragment field file offset = 78
original fragment index     = 0
base image size             = 136 bytes
```

Hashes:

```text
v2 base / count-1  9cb285d78fba5da8a0182745082fc2cd78fef73ad0c996de5af2710c535eb349
v2 count           62219736ce90784cc2440e67b6f566fe35ed385295b44a4180020771d114e1a3
v2 count+1         09e12c1f3fe79d04002f5b8ed274fab9e3eaa6826cf65ab44240ef7533d10244
```

The malformed controls differ from the valid image only in the little-endian four-byte regular-inode `fragment` field at file offset 78:

```text
count-1: 0
count:   1
count+1: 2
```

### Exact-current v2 result

`fragment == count` exits with status 134 under ASan:

```text
ERROR: AddressSanitizer: heap-buffer-overflow
READ of size 4
#0 read_fragment /tmp/sq/squashfs-tools/unsquash-2.c:161
#1 write_file     /tmp/sq/squashfs-tools/unsquashfs.c:1162
...
0x502000000078 is located 0 bytes after 8-byte region
[0x502000000070,0x502000000078)
allocated by:
#1 _malloc             /tmp/sq/squashfs-tools/alloc.h:46
#2 read_fragment_table /tmp/sq/squashfs-tools/unsquash-2.c:89
...
SUMMARY: AddressSanitizer: heap-buffer-overflow
         /tmp/sq/squashfs-tools/unsquash-2.c:161 in read_fragment
```

Controls on the same exact-current binary:

| v2 case | fragment | result |
| --- | ---: | --- |
| `count - 1` | 0 | status 0; extracted byte equals source |
| `count` | 1 | status 134; ASan heap-buffer-overflow in `unsquash-2.c::read_fragment()` |
| `count + 1` | 2 | status 1; `fragment index in inode too large (fragment: 2)`; no ASan report |
| zero-fragment image | no fragment table | status 0; extracted byte equals source |

The zero-fragment control was generated with `-no-fragments`.

## Real v3 reproducer

### Generator provenance

The v3 fixture generator was built from historical squashfs-tools commit:

`26c9d659049def8288455ad8e4766337b721388b`

Commit date/title recorded by the runner:

```text
2007-11-01T06:54:39Z Finally ready for a new release.
```

The generator reports:

```text
mksquashfs version 3.3 (2007/10/31)
```

and generated a little-endian SquashFS 3.1 filesystem.

The same current-compiler compatibility flags were used for the historical generator:

```sh
OLD_CFLAGS='-I. -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_GNU_SOURCE -O2 -fcommon -include sys/sysmacros.h'
make CFLAGS="$OLD_CFLAGS" mksquashfs
```

### Base image

Input tree:

```sh
mkdir /tmp/src-v3
printf Z > /tmp/src-v3/file
./mksquashfs /tmp/src-v3 v3-base.sqfs \
  -noI -noD -noF -nopad -noappend -no-progress
```

Historical-header layout helper:

```text
root_inode=43 fragments=55 inode_table_start=87
reg_size=32 reg_fragment=20 file_type=2
```

Derived fixture details:

```text
fragment_count              = 1
root_inode                  = 0x20
root inode offset           = 32
inode_table_start           = 120
inode metadata header       = 0x803c  (uncompressed)
regular-inode fragment field file offset = 142
original fragment index     = 0
base image size             = 253 bytes
```

Hashes:

```text
v3 base / count-1  33219b296e8bb95ff8937a68bb7b28f87a233be684d8c7263c5ea27325228ae6
v3 count           5fa526ed7f7a8e17e0dcb0a47dedf7c70144865f43a77ddb15f5135c723592da
v3 count+1         c3834fb77f5e2c36d1d9b545ed192032437bc3a1a54cd49d0a804f27480643b3
```

The controls mutate only the four-byte little-endian `fragment` field at file offset 142 to `0`, `1`, or `2`.

### Exact-current v3 result

`fragment == count` exits with status 134 under ASan:

```text
ERROR: AddressSanitizer: heap-buffer-overflow
READ of size 8
#0 read_fragment /tmp/sq/squashfs-tools/unsquash-3.c:171
#1 write_file     /tmp/sq/squashfs-tools/unsquashfs.c:1162
...
0x502000000080 is located 0 bytes after 16-byte region
[0x502000000070,0x502000000080)
allocated by:
#1 _malloc             /tmp/sq/squashfs-tools/alloc.h:46
#2 read_fragment_table /tmp/sq/squashfs-tools/unsquash-3.c:107
...
SUMMARY: AddressSanitizer: heap-buffer-overflow
         /tmp/sq/squashfs-tools/unsquash-3.c:171 in read_fragment
```

Controls on the same exact-current binary:

| v3 case | fragment | result |
| --- | ---: | --- |
| `count - 1` | 0 | status 0; extracted byte equals source |
| `count` | 1 | status 134; ASan heap-buffer-overflow in `unsquash-3.c::read_fragment()` |
| `count + 1` | 2 | status 1; `fragment index in inode too large (fragment: 2)`; no ASan report |
| zero-fragment image | no fragment table | status 0; extracted byte equals source |

The zero-fragment control was generated with `-no-fragments`.

## Minimal candidate

Tracked `candidate.patch` is still the complete source correction:

```diff
diff --git a/squashfs-tools/unsquash-2.c b/squashfs-tools/unsquash-2.c
--- a/squashfs-tools/unsquash-2.c
+++ b/squashfs-tools/unsquash-2.c
@@ -154,7 +154,7 @@ static void read_fragment(...)
-	if(fragment > sBlk.s.fragments)
+	if(fragment >= sBlk.s.fragments)
 		EXIT_UNSQUASH(...);
 
 	fragment_entry = &fragment_table[fragment];

diff --git a/squashfs-tools/unsquash-3.c b/squashfs-tools/unsquash-3.c
--- a/squashfs-tools/unsquash-3.c
+++ b/squashfs-tools/unsquash-3.c
@@ -164,7 +164,7 @@ static void read_fragment(...)
-	if(fragment > sBlk.s.fragments)
+	if(fragment >= sBlk.s.fragments)
 		EXIT_UNSQUASH(...);
 
 	fragment_entry = &fragment_table[fragment];
```

`git diff --check` passed on the exact-current upstream worktree before each candidate rebuild.

## Candidate regression results

The candidate was rebuilt with the same ASan/UBSan command and run against the exact same v2/v3 images.

| reader | case | candidate result |
| --- | --- | --- |
| v2 | `count - 1` | status 0; extracted byte equals source |
| v2 | `count` | status 1; clean corruption error `(fragment: 1)`; no ASan report |
| v2 | `count + 1` | status 1; clean corruption error `(fragment: 2)`; no ASan report |
| v2 | zero fragments | status 0; extracted byte equals source |
| v3 | `count - 1` | status 0; extracted byte equals source |
| v3 | `count` | status 1; clean corruption error `(fragment: 1)`; no ASan report |
| v3 | `count + 1` | status 1; clean corruption error `(fragment: 2)`; no ASan report |
| v3 | zero fragments | status 0; extracted byte equals source |

This is focused end-to-end regression coverage for the boundary: last valid index accepted, first invalid index rejected, larger invalid index remains rejected, and the empty-fragment path remains valid.

The existing tracked `repro.c` remains useful as a reduced count/predicate discriminator; the real parser images above supply the integration-level proof it previously lacked.

## Build and test checks

After the candidate sanitizer runs:

```sh
make -C squashfs-tools clean
make -C squashfs-tools
```

completed successfully at the exact reviewed upstream head with the two-line candidate applied.

The repository also accepts:

```sh
make -C squashfs-tools test
```

On this tree that command compiled `test.c` to a `test` executable via make's implicit rule and exited successfully; it did not run a broader regression suite. The real v2/v3 parser controls above are therefore the relevant behavioral regression coverage for this candidate.

Successful execution evidence is retained in Fieldwork GitHub Actions artifacts:

- v3 run `31563443296`, artifact `lf-629-v3-evidence`, artifact id `9128574051`
- v2 run `31563552566`, artifact `lf-629-v2-evidence`, artifact id `9128611095`

The v2 artifact zip digest reported by Actions is:

```text
09b42ca4bd64f3fe30a54e1247e1faac6ffa35c6b74568c125a920453bb91d03
```

The v3 artifact zip digest reported by Actions is:

```text
370434a9b283eda0485779f19c34cafde4744da5f32fb0e0064844f2a3cc843c
```

## Changed-file fence

### Upstream candidate content

Only these upstream source paths change:

```text
squashfs-tools/unsquash-2.c
squashfs-tools/unsquash-3.c
```

Each path has one `>` to `>=` comparison change.

### Durable Fieldwork candidate

This clean candidate updates only:

```text
investigations/squashfs-tools-legacy-fragment-index-off-by-one/README.md
```

Existing tracked evidence remains unchanged:

```text
investigations/squashfs-tools-legacy-fragment-index-off-by-one/candidate.patch
investigations/squashfs-tools-legacy-fragment-index-off-by-one/repro.c
```

### Disposable execution machinery

The temporary workflow used to obtain the real parser evidence lives only on the disposable branch `lf-629-repro-exec`:

```text
.github/workflows/lf-629-repro.yml
```

It is excluded from the clean candidate.

## Evidence boundary

Demonstrated:

- `sBlk.s.fragments` is an entry count in both legacy fragment-table readers;
- valid indexes are `0 .. count - 1`;
- exact-current v2/v3 use `fragment > sBlk.s.fragments` before indexing;
- exact-current v4 uses the expected `>=` count boundary;
- real malformed v2 and v3 images with `fragment == count` reach the one-past table read under ASan;
- `count - 1` is accepted, `count + 1` is already rejected, and zero-fragment images are accepted;
- the two-line `>=` candidate rejects `count` before the access while preserving all controls;
- exact-current candidate sanitizer builds and the normal full build succeed;
- relevant recent history and issue/PR overlap were inspected.

Claim made: out-of-bounds read on malformed filesystem input.

No exploitability conclusion is drawn from this evidence.

## Current disposition

State: **CLEAN CANDIDATE READY FOR INDEPENDENT REVIEW**

Candidate: existing two-line `candidate.patch` (`>` -> `>=` in v2/v3 `read_fragment()`).

Execution evidence: exact-current real v2/v3 parser inputs under ASan/UBSan, with boundary and zero-fragment controls, retained in the successful Fieldwork Actions runs above.

External-contact state: no upstream interaction authorized or made.
