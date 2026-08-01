# Handoff

## State

- Investigation: kmod nested modprobe configuration identity
- State: `EXECUTING`
- Linux Fieldwork branch: `investigation/kmod-modprobe-options-config-path`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact technical head before this handoff commit: `1e59ba92f50d3aada6893de25d27afb7b75e1571`
- Internal draft PR: #412
- External-contact state: unauthorized; none made

## What was created

- kmod added to `targets/registry.yml` as an active target;
- durable source/test map at `targets/kmod/map.md`;
- investigation record and executable test under `investigations/kmod-modprobe-options-config-path/`;
- deterministic root result, immediate rerun, and unprivileged receipt;
- broader shortlist at `notes/foundational-codebase-frontier-2026-08-01.md` covering kmod, shadow, procps-ng, libcap, and iproute2.

## Exact upstream identities

- Canonical repository: `https://git.kernel.org/pub/scm/utils/kernel/kmod/kmod.git`
- Source-reading mirror: `https://github.com/kmod-project/kmod.git`
- Mirror master observed 2026-08-01: `5086df53090b2fe9fa1c31351c05a78a12a4ba71`
- Relevant source: `tools/modprobe.c`
- Intent/documentation commit: `42d60a3267162a36ec6b6b39a7b91e5078b90979`
- Current local executable: Debian `kmod 34.2-2`, `/usr/sbin/modprobe`
- Local executable SHA-256: `a775c12b9d71d9548654ff98ecc0e5e3378bdaccd52ccb62fa80a5f41e849caf`

## Latest distinguishing result

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

A manually quoted spaced path in `MODPROBE_OPTIONS` is a passing control. Leading/repeated spaces, tabs, and unmatched quotes all silently lose the marker while status remains 0.

The normalized root run and immediate rerun are byte-identical. The same decision-changing fields reproduce as EUID 65534. No module insertion or removal occurs.

## Exact evidence identities

```text
test SHA-256: 8006c8cb24ef44803565fb580bd9334edb807e210f3a5c0f313679f260c211c1
root result SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
immediate rerun SHA-256: c6ffd6ac62937b2ceb78786fe3b7610b5125f91db356f1f747c69fe4fe8286bc
unprivileged result SHA-256: 759550141d24d03543d0686b235e82b0aab8015181b50bddb169e9d297acd9cf
```

## Interpretation

The demonstrated defect is not that kmod rejects a spaced configuration directory. The parent accepts it. The defect is that kmod's own recursive install/remove transport flattens the valid pathname into an unquoted environment string, changing argv identity for the nested command. Both commands return success, so status-only evidence misses the policy change.

Current master still contains the same raw append and custom parser, but master has not yet been built or executed in this runtime.

## First incomplete step

Obtain/build exact kmod master `5086df53090b2fe9fa1c31351c05a78a12a4ba71` and run the retained test unchanged against that build.

Then:

1. integrate the regression into `testsuite/test-modprobe.c` and the fake rootfs harness;
2. require a losing exact-master baseline;
3. compare complete propagation mechanisms, including quote-containing paths, repeated whitespace, existing environment content, and multiple `-C` values;
4. run the focused test with sanitizer-enabled GCC and Clang builds;
5. retain cleanup/rerun and exact source/artifact identities;
6. recheck active upstream issues and pull requests before any publication decision.

## Cleanup

All temporary configuration directories, helper scripts, nested outputs, and environment receipts were removed. No process, module, mount, socket, lock, or persistent host configuration remains.

## Authority

PR #412 is an internal Linux Fieldwork review surface. No upstream issue, email, patch, pull request, comment, review, or other contact is authorized or performed.
