# Handoff

## Unit state

`RETIRED`

Unit 09 is technically complete and should not be submitted upstream. Canonical mmdebstrap `develop` already contains the equivalent correction.

## Exact identities

```text
Linux Fieldwork branch: upstream/unit-09-dev-ptmx-bsdutils
Linux Fieldwork base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
packet: upstream-packets/units/09-dev-ptmx-bsdutils/
canonical main: 77ec9be5417ee44c96343d2347145585da1b1f94
canonical develop: 6e1e572bc49456daab7fd1274b1f3b8ec4a1c248
canonical owning commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
canonical corrected blob: 258a7f9579b2a2b91b6758952851296b44197ae0
external-contact state: none occurred
```

The issue `#397` unit checkpoint records the final Linux Fieldwork branch head after closeout commits.

## Canonical successor

```text
commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
parent: 6de6403eca9d606a88ce8f6eb0bba097d9f7369e
author: Johannes Schauer Marin Rodrigues <josch@mister-muffin.de>
author date: 2025-11-16T00:04:44+01:00
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
reachable from: refs/heads/develop, refs/tags/1.5.7+develop
```

Exact hunk:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
```

Canonical `main` still contains baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`. The branch distinction explains why the downstream GitHub fork and stable main appeared unfixed while canonical development already owned the work.

## Canonical audit receipt

```text
internal PR: 411
branch: investigation/mmdebstrap-canonical-audit-unit09
carrier head: 8c8b8a1753881b86f1d5628be659a98fbcc02c6f
workflow run: 30704384974
job: 91380861751
artifact: 8819850852
artifact digest: sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b
```

The audit performed read-only mirror clones, ref inventory, full path-history inspection, exact content extraction, and public tracker/BTS/list searches. See `artifacts/CANONICAL-FORGEJO-AUDIT.md`.

## Preserved Linux Fieldwork evidence

Controlled downstream candidate:

```text
repository: teamleaderleo/mmdebstrap
base: 574048f2a720057b75e56622003932f344dc700a
base blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate branch: linux-fieldwork/unit-09-dev-ptmx-bsdutils
candidate commit: 43082a6bc959e2d7cefae48f52e045cc90869287
candidate blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
```

Static validation:

```text
workflow run: 30690010699
result: patch validation, compilation, full unit suite, shell/help checks passed
```

Current-sid execution and rerun:

```text
run 30690241513; artifact 8815599405; root/unshare PASS
run 30690452822; artifact 8815724078; root/unshare PASS
```

Both runs used `mmdebstrap 1.5.7-3` and `bsdutils 1:2.42.2-2`; both inner `script` hooks succeeded and every generated root was removed. See `artifacts/CURRENT-SID-DOUBLE-PASS.md`.

## Classifier lesson

The audit's first machine summary searched only Linux Fieldwork's package ordering and missed canonical's appended ordering. Full path history corrected the result. Future overlap checks should search package membership or inspect the complete file history rather than require one comma ordering.

Broad substring searches also produced unrelated tracker/list hits. Exact source ancestry and patches outrank raw term counts.

## Closeout actions

- `upstream-packets/INDEX.md`: set unit 09 to `RETIRED`.
- Issue `#397`: checkpoint set to `RETIRED` with canonical successor.
- Internal PR `#411`: close as completed audit carrier.
- Optional direct-run PR `#407`: close as unnecessary after preserving any completed receipt.
- Controlled downstream fork branch: retain as historical evidence; no pull request.

## Future action

No technical or submission work remains for unit 09. Normal observation of canonical `develop` promotion is optional and requires no upstream contact. Reopen only if canonical history is rewritten or the correction disappears.

## Authorization boundary

No mmdebstrap or Debian upstream issue, pull request, merge request, comment, review, email, mailing-list post, or other external contact was created.
