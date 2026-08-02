# Handoff

## State

- Investigation: kmod nested modprobe configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact execution-carrier head before this handoff update: `fdd6d81a930d4ebafba81eb8d37bf1b3f31341c4`
- Internal draft PR: #412
- External-contact state: unauthorized; none made

## What exists

- kmod target map and registry entry;
- durable investigation record and deterministic package-level probe;
- root, EUID 65534, quoted-control, parser-control, cleanup, and immediate-rerun receipts;
- exact-master GCC/Clang sanitizer execution workflow at `.github/workflows/kmod-modprobe-config-path.yml`.

## Exact upstream identities

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `https://github.com/kmod-project/kmod.git`
- Exact mirror master under test: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Relevant source: `tools/modprobe.c`
- Intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`
- Current local executable: Debian `kmod 34.2-2`, `/usr/sbin/modprobe`
- Local executable SHA-256: `a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf`

## Latest demonstrated result

```text
no-space config:
  direct marker=1
  parent status=0
  nested status=0
  nested marker=1

spaced config:
  direct marker=1
  parent status=0
  nested status=0
  nested marker=0
  MODPROBE_OPTIONS=-C $TMP/space/conf dir
```

A manually quoted spaced path is a passing control. Leading/repeated spaces, tabs, and unmatched quotes silently lose the selected configuration while status remains 0. Root and EUID 65534 agree. No module insertion or removal occurs.

## Exact retained evidence

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Exact-master execution carrier

Workflow run `30759618540` was queued at the latest observation for head `fdd6d81a930d4ebafba81eb8d37bf1b3f31341c4`.

The workflow:

1. checks out Linux Fieldwork without persisted credentials;
2. checks out exact `kmod-project/kmod@5086df53090b2fe9fa1c31351c05a78a12a4ba71` read-only;
3. records the source head and `tools/modprobe.c` blob;
4. builds with GCC and Clang using AddressSanitizer and UndefinedBehaviorSanitizer;
5. requires the retained unchanged probe to run against the built `build-<compiler>/modprobe`;
6. runs the discriminator twice and requires byte-identical normalized results;
7. verifies cleanup and an unchanged target source tree;
8. uploads exact source, binary, result, environment, and digest receipts.

No queued run is treated as a result.

## Interpretation

The package-level evidence identifies argument serialization as the owner: kmod flattens a valid `-C` pathname into an unquoted environment string for its own recursive install/remove transport. The nested custom parser receives different arguments, falls back to another policy, and still exits successfully.

The exact-master workflow will determine whether the same behavior is executable at the pinned current source revision. It does not yet select a repair.

## First incomplete step

Read workflow `30759618540` when terminal.

- If both compiler jobs reproduce the loss without sanitizer findings, retain job/artifact identities and move to a native `testsuite/test-modprobe.c` regression plus candidate comparison.
- If setup/build fails, repair only the dependency or workflow owner and rerun unchanged product logic.
- If source behavior differs, preserve the exact result and reclassify the current-source boundary before changing a candidate.

After exact-master execution:

1. integrate the regression into kmod's native fake-root/fake-syscall testsuite;
2. compare complete propagation mechanisms, including quote-containing paths, repeated whitespace, existing environment content, and multiple `-C` values;
3. retain sanitizer, cleanup, rerun, and exact artifact identities;
4. recheck active upstream issues and pull requests before any publication decision.

## Cleanup

All local temporary configuration directories, helper scripts, nested outputs, and receipts were removed. The new work is hosted read-only execution machinery; no process, module, mount, socket, lock, or persistent host configuration remains.

## Authority

PR #412 and the workflow are internal Linux Fieldwork surfaces. No upstream issue, email, patch, pull request, comment, review, or other contact is authorized or performed.
