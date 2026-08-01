# Unit 09 — mmdebstrap dev-ptmx declares bsdutils

## State

`RETIRED`

Canonical mmdebstrap already contains the equivalent correction on `develop`. No external submission should be created.

## Canonical successor

```text
repository: josch/mmdebstrap on Muffin Forgejo
main head: 77ec9be5417ee44c96343d2347145585da1b1f94
develop head: 6e1e572bc49456daab7fd1274b1f3b8ec4a1c248
owning commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
author date: 2025-11-16T00:04:44+01:00
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
resulting tests/dev-ptmx blob: 258a7f9579b2a2b91b6758952851296b44197ae0
also present on tag: 1.5.7+develop
```

Canonical hunk:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
```

Canonical `main` still carries baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`, while `develop` contains the fix. The downstream GitHub fork followed the older Deepin `1.5.7-3` import and therefore omitted later canonical development history.

## Read-only canonical audit

```text
internal audit PR: 411
workflow run: 30704384974
job: 91380861751
artifact: 8819850852
artifact digest: sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b
carrier head: 8c8b8a1753881b86f1d5628be659a98fbcc02c6f
```

The audit mirror-cloned canonical Forgejo and Debian Salsa repositories, inventoried all refs, inspected complete `tests/dev-ptmx` history, and captured public tracker, BTS, and mailing-list searches. Full path history found the existing canonical commit. The initial summary's exact pickaxe missed it because Linux Fieldwork placed `bsdutils` first while canonical appended it.

Detailed receipt:

```text
artifacts/CANONICAL-FORGEJO-AUDIT.md
```

## Historical owner

Recovered Debian CI run `72574145` tested `mmdebstrap 1.5.7-3` on Debian testing amd64. Its first and only failure was `(252/283) dev-ptmx --mode=root --variant=apt` after the generated root omitted `bsdutils` and attempted inner-root `script(1)`:

```text
chroot: failed to run command ‘script’: No such file or directory
```

`bsdutils` provides `/usr/bin/script`; the Essential-set transition exposed the undeclared fixture dependency.

## Linux Fieldwork candidate and evidence

Controlled downstream carrier:

```text
repository: teamleaderleo/mmdebstrap
base: master at 574048f2a720057b75e56622003932f344dc700a
base blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate branch: linux-fieldwork/unit-09-dev-ptmx-bsdutils
candidate commit: 43082a6bc959e2d7cefae48f52e045cc90869287
candidate blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
compare: one commit, one file, one insertion, one deletion
```

Linux Fieldwork used equivalent package-set semantics with `bsdutils` first:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=bsdutils,gcc,libc6-dev,python3,passwd \
```

Retained evidence:

- `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch`
- `tests/test_mmdebstrap_dev_ptmx_dependency.py`
- `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py`
- `artifacts/CURRENT-SID-DOUBLE-PASS.md`
- `artifacts/CANONICAL-FORGEJO-AUDIT.md`

Static packet validation passed run `30690010699`. Two separate current-sid containers then passed root and unshare variants with `mmdebstrap 1.5.7-3` and `bsdutils 1:2.42.2-2`:

```text
run 30690241513; artifact 8815599405
run 30690452822; artifact 8815724078
```

Both inner `script` hooks succeeded and every generated root was removed.

## Disposition

- External mmdebstrap submission: retired as already implemented.
- Controlled GitHub candidate: historical evidence only; do not propose it upstream.
- Optional direct run PR `#407`: close as unnecessary after preserving any completed receipt.
- Canonical audit PR `#411`: close as completed evidence carrier.
- Future tracking: observe normal canonical promotion from `develop`; no contact is required.

## Authority

No mmdebstrap or Debian upstream issue, pull request, comment, email, review, mailing-list message, or other contact was created.
