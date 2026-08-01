# Canonical Forgejo audit — unit 09

## Disposition

`RETIRED`

The proposed external submission is superseded by an existing canonical mmdebstrap commit on `develop`.

## Read-only audit identity

```text
Linux Fieldwork audit PR: 411
workflow run: 30704384974
job: 91380861751
artifact: 8819850852
artifact digest: sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b
carrier head: 8c8b8a1753881b86f1d5628be659a98fbcc02c6f
```

The audit mirror-cloned canonical Forgejo and Debian Salsa repositories, inventoried every advertised ref, inspected complete `tests/dev-ptmx` history, ran exact pickaxe and regex searches, and captured public tracker, BTS, and mailing-list search responses. It performed read-only public fetches and created no upstream contact.

## Canonical branch identities

```text
main:    77ec9be5417ee44c96343d2347145585da1b1f94
         subject: Take hurdfiles on hurd-amd64 as well

develop: 6e1e572bc49456daab7fd1274b1f3b8ec4a1c248
         subject: Create pax tar archives with --sparse
```

Canonical `main` has the exact historical baseline file:

```text
tests/dev-ptmx blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
SHA-256: cb3808cff2cbff5d206931fb3b86a65cbe796becc3f143441558c8c941252f03
include: gcc,libc6-dev,python3,passwd
inner script -c hooks: 2
```

Canonical `develop` and tag `1.5.7+develop` contain the correction:

```text
include: gcc,libc6-dev,python3,passwd,bsdutils
resulting tests/dev-ptmx blob: 258a7f9579b2a2b91b6758952851296b44197ae0
```

## Canonical owning commit

```text
commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
parent: 6de6403eca9d606a88ce8f6eb0bba097d9f7369e
author: Johannes Schauer Marin Rodrigues <josch@mister-muffin.de>
author date: 2025-11-16T00:04:44+01:00
committer date: 2025-11-16T10:38:01+01:00
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
```

Exact canonical hunk:

```diff
diff --git a/tests/dev-ptmx b/tests/dev-ptmx
index ca1cde0..258a7f9 100644
--- a/tests/dev-ptmx
+++ b/tests/dev-ptmx
@@ -119,7 +119,7 @@ END
 # use script to create a fake tty
 # run all tests as root and as a normal user (the latter requires ptmxmode=666)
 script -qfec "$prefix {{ CMD }} --mode={{ MODE }} --variant=apt \
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
 	--customize-hook='chroot "\$1" useradd --home-dir /home/user --create-home user' \
```

The Linux Fieldwork candidate placed `bsdutils` first. Package-set semantics are equivalent; canonical ownership and ordering take precedence.

## Ref evidence

```text
refs/heads/main:tests/dev-ptmx:122:
    --include=gcc,libc6-dev,python3,passwd \

refs/heads/develop:tests/dev-ptmx:122:
    --include=gcc,libc6-dev,python3,passwd,bsdutils \

refs/tags/1.5.7+develop:tests/dev-ptmx:122:
    --include=gcc,libc6-dev,python3,passwd,bsdutils \
```

## Search interpretation

The first audit summary incorrectly reported `corrected_include_history_present=false` because its exact pickaxe searched only the Linux Fieldwork ordering `bsdutils,gcc,...`. Full path-history inspection found the canonical appended ordering above. Broad tracker and mailing-list regex counts also contained false positives such as `pty` inside unrelated words. Exact source history is the decisive evidence.

No new mmdebstrap issue or pull request is warranted. Retain the historical Debian failure, controlled-fork candidate, static regression, and current-sid double pass as independent confirmation of the already-landed canonical correction.
