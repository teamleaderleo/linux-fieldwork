# Candidate receipt — libblkid Minix v3 opposite-endian detection

Date: 2026-08-11

Internal tracking: `teamleaderleo/linux-fieldwork#570`

## Canonical candidate

- Repository: `teamleaderleo/util-linux`
- Branch: `linux-fieldwork/libblkid-minix3-endian-clean`
- Base: `53e442154c97b872b529a9f61e335d150ad0f742`
- Head: `e47d4b1711b37b3928b90f56586c361a0623d35a`
- Commit message: `libblkid: detect opposite-endian Minix v3`
- Changed file: `libblkid/src/superblocks/minix.c`
- Product diff: exactly one line, one comparison

```diff
- if (sb3->s_magic == MINIX3_SUPER_MAGIC)
+ if (swab16(sb3->s_magic) == MINIX3_SUPER_MAGIC)
```

Exact commit review confirms there are no whitespace, EOF, test, workflow, receipt, or unrelated source changes on this branch.

## Superseded carrier

Earlier head `eebfe13d1dd1c15dc66976723f1e3d001f6fc121` on `linux-fieldwork/libblkid-minix3-endian` carried the same semantic hunk but also removed the file's final blank line because of whole-file connector replacement.

Retain that head only as provenance. The `-clean` branch above is the review candidate.

## Runtime evidence paired with this candidate

`CURRENT_RUNTIME_RESULTS.md` retains the four-cell installed-libblkid probe:

```text
v1 LE -> detected, LITTLE
v1 BE -> detected, BIG
v3 LE -> detected, LITTLE
v3 BE -> unrecognized, rc=2
```

The clean candidate has not yet been compiled against current util-linux. Its next required gate is to run that exact four-cell fixture against a build from `e47d4b1711b37b3928b90f56586c361a0623d35a` and confirm v3 BE becomes `VERSION=3`, `ENDIANNESS=BIG` while the three controls remain unchanged.

## Packaging boundary

No DCO/sign-off identity was inferred or synthesized. The candidate is internal evidence until a configured or explicitly chosen contributor identity is available and a human authorizes any upstream interaction.

## Authority

No upstream contact is authorized or made.
