# squashfs-tools v3/v4 large-file block-count overflow

Date: 2026-08-12
Issue: #633
State: CLEAN CANDIDATE READY FOR INDEPENDENT REVIEW

## TL;DR

Exact-current `plougher/squashfs-tools@5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491` was exercised with real crafted SquashFS v3.1 and v4.0 images under Clang ASan/UBSan plus implicit-integer-conversion sanitizers.

Both legacy/current large-regular-inode readers have two related arithmetic failures in their block-count calculation:

1. with `fragment == SQUASHFS_INVALID_FRAG`, the ceiling expression `file_size + block_size - 1` can signed-overflow for a nonnegative 64-bit `file_size` such as `LLONG_MAX`;
2. either calculation branch can produce more than `INT_MAX` blocks and then assign that wide count to the common signed `int inode.blocks` field.

The executed v3 and v4 controls reproduce both boundaries. A narrow candidate computes the count without the overflowing ceiling addition, keeps it wide until a checked `INT_MAX` rejection, and only then assigns it to `inode.blocks`.

Observed impact: malformed filesystem input can trigger signed arithmetic undefined behavior or an out-of-range block-count conversion in the reader. No exploitability claim is made.

No upstream contact or mutation was made.

## Exact source identity

- Fieldwork clean-candidate base: `1ae906f23e765908c8a44cf870d78ed73262f83e`
- tested and refreshed upstream master: `5436ec0e5bf50dd8f7fe182d9ffd92b0861cb491`
- historical v3 image generator: `26c9d659049def8288455ad8e4766337b721388b` (`Finally ready for a new release.`, 2007-11-01)

The upstream head remained unchanged when refreshed after execution.

## Source boundary

In both `squashfs-tools/unsquash-3.c` and `squashfs-tools/unsquash-4.c`, `SQUASHFS_LREG_TYPE` first rejects negative `file_size`, then computes:

```c
i.blocks = inode->fragment == SQUASHFS_INVALID_FRAG ?
    (inode->file_size + sBlk.s.block_size - 1) >> sBlk.s.block_log :
    inode->file_size >> sBlk.s.block_log;
```

The on-disk v3/v4 large regular inode stores `file_size` as signed `long long`. The common reader stores the result in:

```c
struct inode {
    int blocks;
    ...
};
```

`write_file()` and `cat_file()` later use `inode->blocks` for the block-list allocation, `read_block_list()`, and loop bounds.

These are separate from #629's fragment-table index boundary and #632's 32-bit fragment-table allocation-width boundary.

## Real fixture construction

The fixture does not create a physically huge source file. A one-byte regular file plus a hard link forces `mksquashfs` to encode a large regular inode (`SQUASHFS_LREG_TYPE`, inode type 9, `nlink=2`). The generated inode metadata is uncompressed, allowing one exact field mutation.

Base source:

```sh
printf Z > file
ln file file-hardlink
```

Two layouts were generated for each version:

- no-fragment: `fragment == SQUASHFS_INVALID_FRAG` to exercise the ceiling branch;
- fragment-present: `fragment == 0` to exercise the floor branch independently.

Only the eight-byte little-endian `file_size` field was changed in each crafted image.

Observed layout at the tested generators:

| Version | branch | block size | file_size absolute offset | inode type | fragment | nlink |
|---|---|---:|---:|---:|---:|---:|
| v4 | no fragment | 131072 | 123 | 9 | 4294967295 | 2 |
| v4 | fragment | 131072 | 123 | 9 | 0 | 2 |
| v3 | no fragment | 131072 | 154 | 9 | 4294967295 | 2 |
| v3 | fragment | 131072 | 154 | 9 | 0 | 2 |

At a 131072-byte block size:

- exact `INT_MAX` blocks: `281474976579584` bytes;
- one byte past the no-fragment ceiling boundary: `281474976579585` bytes;
- exact `INT_MAX + 1` full blocks: `281474976710656` bytes;
- signed-overflow discriminator: `9223372036854775807` (`LLONG_MAX`).

The parser command intentionally uses listing mode:

```sh
./unsquashfs -processors 1 -no-progress -ll IMAGE
```

That reaches `read_inode()` and its block-count arithmetic without attempting to allocate or extract hundreds of terabytes. Downstream extraction consumers were source-reviewed; no huge allocation/extraction was attempted.

## Sanitizer build

Runner: Ubuntu 24.04.4, Linux 6.17.0-1020-azure, Clang 18.1.3, GCC 13.3.0, Git 2.54.0.

```sh
SAN='-O1 -g -fsanitize=address,undefined,implicit-integer-truncation,implicit-integer-sign-change -fno-sanitize-recover=all -fno-omit-frame-pointer'
make -C squashfs-tools -j2 CC=clang \
  EXTRA_CFLAGS="$SAN" \
  EXTRA_LDFLAGS='-fsanitize=address,undefined,implicit-integer-truncation,implicit-integer-sign-change' \
  unsquashfs

export ASAN_OPTIONS='halt_on_error=1:abort_on_error=1:detect_leaks=0'
export UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'
```

## Unpatched execution

Disposable run 1:

- workflow run `31569618973`
- job `94028608421`
- artifact `lf-633-runtime-evidence`, ID `9130805622`
- artifact ZIP SHA256 `fe94bf615703315641ade4729ce31213f2abbf549eae63fc8e36d4aa1998383f`

For both v3 and v4, the no-fragment matrix showed:

- base one-byte image: accepted, sanitizer-clean;
- exact `INT_MAX` blocks: accepted, sanitizer-clean;
- `INT_MAX + 1` blocks: abort under implicit-conversion sanitizer;
- `LLONG_MAX`: abort under UBSan signed-overflow detection in the ceiling expression.

Disposable run 2 additionally executed the fragment-present branch. Both readers reported the same conversion failure at `2^31` blocks:

```text
runtime error: implicit conversion from type 'long long' of value 2147483648
(64-bit, signed) to type 'int' changed the value to -2147483648
```

The v4 trace points at `unsquash-4.c:249` and the v3 trace at `unsquash-3.c:328`, both from `read_inode()`, then `dir_scan()` and `main()` in the common reader.

## Candidate

The retained `candidate.patch` changes only `unsquash-3.c` and `unsquash-4.c`.

For each `SQUASHFS_LREG_TYPE` case it:

1. computes the floor block count in `long long` using the existing validated power-of-two block geometry;
2. adds one only when the no-fragment case has a remainder, avoiding `file_size + block_size - 1`;
3. rejects `blocks > INT_MAX` before the signed-int assignment;
4. assigns the checked value to `i.blocks`.

The count remains exactly equivalent for representable valid values. The exact `INT_MAX` boundary remains accepted in both fragment branches.

## Candidate execution

Disposable candidate run:

- workflow run `31569949594`
- job `94029580008`
- disposable branch head `d396f229be294f14195d58248ccc439bcfb215e5`
- artifact `lf-633-candidate-evidence`, ID `9130912216`
- artifact ZIP SHA256 `3f764b93b78755b636ebee2375a470f6b4b662193c9263c646f40abed3182bf5`

`git diff --check` passed and the upstream changed-file fence was exactly:

```text
squashfs-tools/unsquash-3.c
squashfs-tools/unsquash-4.c
```

A normal full `make -C squashfs-tools -j2` passed before the sanitized candidate rebuild.

Candidate matrix, for both v3 and v4:

| Branch / input | Result |
|---|---|
| no-fragment base | accepted; sanitizer-clean |
| no-fragment exact `INT_MAX` blocks | accepted; sanitizer-clean |
| no-fragment `INT_MAX * block_size + 1` | rejected cleanly as block count 2147483648 |
| no-fragment `LLONG_MAX` | rejected cleanly before overflow |
| fragment-present base | accepted; sanitizer-clean |
| fragment-present exact `INT_MAX` blocks | accepted; sanitizer-clean |
| fragment-present `(INTMAX + 1) * block_size` | rejected cleanly as block count 2147483648 |

Every candidate rejection log was checked for absence of ASan/UBSan/runtime-error output. The run ended with:

```text
ALL LF-633 CANDIDATE ASSERTIONS PASSED
```

## Fixture hashes from candidate run

```text
03d54cf3763294eba20b01900b89f50790f1267f023174ebf671302ea438c6d3  v3-frag-intmax.sqfs
1069defcff4bb973ee4b4e1b69e21268fbce9ff2f1cbc15e910057ba391c439c  v3-frag-plusblock.sqfs
2a93b40cf518182c66ac3e8a6c29c43928fb13f71ed6a03fb10184732779afc9  v3-frag-base.sqfs
3914115f07e1c462c368d8e77db101bbe894ee622d72ee1a06ddff53e4dad89e  v3-nofrag-base.sqfs
6f4a01c6592f60a46ccaa8984b4a50e630c07eb1086cb9bc9d21a82791ecb452  v3-nofrag-plusbyte.sqfs
a114c0dc38ea5cb951dbf6f9ea5e72432e047832f20e58835be418f2127371d9  v3-nofrag-llmax.sqfs
b9389081635c56fd84f3e991197e8a3a3e019498ca46c630b17f41afc05d7b58  v3-nofrag-intmax.sqfs
5ec8bc93f05fc2623c38106bc0501966c2f74152493a9253eaf02184403ed5f4  v4-frag-base.sqfs
8f07d855aee362852aaecaafa2fc0541cd5b0193e1a93257e5cea99596e61694  v4-frag-intmax.sqfs
b1439e35cc9d0a39ce49240730b07866153e350c14d773ccf20540bb60299ac0  v4-frag-plusblock.sqfs
74e64297d8cc2e86b9d788de1a513c3752abc8d66b3e6c8cd3ea94d39050937c  v4-nofrag-base.sqfs
bbe74d39e2ae77a550125cfddb170fc63af8161fc526628a07bbf321b675ff47  v4-nofrag-intmax.sqfs
a5cf65a0a6a71fcd4356d2e8eb4916a3c8ddaae2864362c940d73d4769ae4178  v4-nofrag-plusbyte.sqfs
3869d1b0d620cd9602f33a8df55ae26a77a03289547327c6def21a437db55582  v4-nofrag-llmax.sqfs
```

## Review boundary

This record establishes exact-current parser reachability, the two arithmetic/representation failures, and a focused candidate with positive and negative boundary controls. It does not claim exploitability and does not attempt enormous extraction or allocation.

The disposable workflow exists only to produce retained execution evidence and is removed from the execution-branch tip after artifact retention.

## Changed-file fence

Clean Fieldwork candidate should contain only:

```text
investigations/squashfs-tools-large-file-block-count-overflow/README.md
investigations/squashfs-tools-large-file-block-count-overflow/candidate.patch
```

No upstream files are committed into Fieldwork. No upstream interaction has occurred.

## Disposition

**CLEAN CANDIDATE READY FOR INDEPENDENT REVIEW**
