# LF-SCOUT-DEB-02 — LF-12 reproducible package variance

## In simple words

A tiny Debian source package was built repeatedly while changing practical environmental inputs. The `.deb` stayed byte-identical across elapsed time, build path, locale, timezone, a hostname environment value, a real build-user change, file creation order, and serial versus four-job compilation.

Changing `SOURCE_DATE_EPOCH` by one day changed archive timestamps while installed file bytes and package control data stayed equal. That difference follows a declared input, so the decision is `stop` rather than promote a source fix.

## Scout identity and home lane

- Scout-ID: `LF-SCOUT-DEB-02`
- Home lane: `LF-12`
- Working branch: `scout/lf-scout-deb-02/lf-12-reproducible-package-variance`
- Reviewer: `LF-SCOUT-FS-01`

## Exact source or package boundary

The probe generates native Debian source package `lf12-variance-probe` version `1.0` (`3.0 (native)`) and produces `lf12-variance-probe_1.0_amd64.deb`.

The fixture contains two independently compiled C translation units, one header, two deterministic documentation files, a small Makefile, and manual Debian rules. The two object targets make the parallelism variant exercise real concurrent compilation.

- Architecture: `amd64`
- Changelog timestamp: `Thu, 30 Jul 2026 04:30:00 +0000`
- Default `SOURCE_DATE_EPOCH`: `1785385800`
- Alternate epoch: `1785299400`
- Build command: `dpkg-buildpackage -us -uc -b`

## Environment and privileges

Retained baseline:

- Debian GNU/Linux 13 (`trixie`)
- kernel `Linux 6.12.13`
- `amd64`
- `dpkg` / `dpkg-dev` `1.22.22`
- GCC package `4:14.2.0-1`
- GNU make `4.4.1-2`
- tar `1.35+dfsg-3.1`

Most builds ran as root in a disposable container. The user variation ran the complete build as `nobody:nogroup`. `Rules-Requires-Root: no` plus `dpkg-deb --root-owner-group` normalized package ownership. Exact retained metadata is in `artifacts/environment.txt`.

## Source and test map

`artifacts/run-variance-probe.sh` generates the package, runs ten builds, and compares:

1. complete `.deb` bytes with `sha256sum` and `cmp`;
2. unpacked payload with `dpkg-deb -x` and `diff -qr`;
3. control data with `dpkg-deb -e` and `diff -qr`;
4. archive metadata with `ar tv` and `dpkg-deb --fsys-tarfile | tar --full-time -tvf -`;
5. `.buildinfo` and `.changes` as separate build-event metadata.

The script asserts expected package, payload, and control equalities; verifies that the parallel build invoked `make -j4`; and rejects cleanup roots outside `/tmp` or `/var/tmp`. `tests/test_lf12_probe_safety.py` exercises the destructive-path boundary.

## Probe design and distinguishing outcomes

The matrix names these intended factors:

- elapsed time;
- build path;
- locale;
- timezone;
- hostname environment;
- build user;
- input file creation order;
- parallel build scheduling;
- declared source epoch.

Most non-baseline variants also use distinct run paths. The path-only control shows that path changes do not alter the package in this fixture, but this residual coupling means those rows are not described as perfectly isolated one-factor experiments.

A `.deb` difference with equal unpacked bytes points to archive metadata or compression. A payload difference would point toward source, compiler, generator, or staging behavior. A difference confined to `.buildinfo` or `.changes` is build-event metadata rather than package-content variance.

## Commands or scripts

Run locally in a suitable Debian environment:

```sh
bash artifacts/run-variance-probe.sh /tmp/lf12-variance-run
```

The dedicated workflow `.github/workflows/lf-12-package-variance.yml` runs the matrix in a Debian 13 container and uploads compact evidence.

Retained records:

- `artifacts/run-variance-probe.sh`
- `artifacts/environment.txt`
- `artifacts/variance-matrix.tsv`
- `artifacts/diff-summary.txt`

Generated packages, extracted trees, and verbose logs remain in the disposable caller work directory.

## Observed results

Two same-path, same-environment builds separated by more than two seconds produced the same `.deb`:

```text
f17ed57c41409123ca03804b96d3475094e2e82fca6967155581233e720d9afb
```

Unpacked data and control data were equal. `.buildinfo` differed at `Build-Date`; `.changes` differed because it records build-event metadata and checksums.

| Variant | `.deb` | Unpacked bytes | Control | First difference |
|---|---:|---:|---:|---|
| elapsed time | same | same | same | `.buildinfo: Build-Date` |
| build path | same | same | same | `.buildinfo: Build-Date` |
| locale | same | same | same | `.buildinfo: Environment/LC_ALL` |
| timezone | same | same | same | `.buildinfo: Build-Date` |
| hostname env | same | same | same | `.buildinfo: Build-Date` |
| user `nobody` | same | same | same | `.buildinfo: Build-Date` |
| file creation order | same | same | same | `.buildinfo: Build-Date` |
| parallelism, two object files | same | same | same | `.buildinfo: Environment/DEB_BUILD_OPTIONS` |
| source epoch minus one day | different | same | same | archive timestamps |

The alternate epoch package hash was:

```text
fe485dca144bbef19c5ba03baba1e63677b0c89fbcc536a8fd0bf487b18a590f
```

## First meaningful difference

Changing `SOURCE_DATE_EPOCH` from `1785385800` to `1785299400` moved outer `ar` member timestamps and every data-tar member timestamp back one day. The executable, documentation, and control data remained equal after extraction.

Classification:

- source behavior: unchanged;
- build-system behavior: compiler output stayed equal across path and real parallelism changes;
- packaging behavior: `dpkg-deb` applied the declared source epoch to archive timestamps;
- declared input variation: package checksums reflect that changed timestamp input.

## Interpretation

The supported packaging path normalized the practical ambient differences exercised by this fixture. `.buildinfo` and `.changes` describe a build event and should be evaluated separately from the `.deb` reproducibility result.

The only package variance followed an explicitly changed timestamp input. No source or packaging defect was demonstrated.

## Evidence limits

- Controlled native fixture rather than an archive source package.
- One architecture, distribution release, compiler family, and dpkg version.
- No `diffoscope` or `reprotest`; the fixture uses complete package bytes, extraction, control comparison, and archive listings.
- Hostname coverage is the `HOSTNAME` environment surface, not a changed UTS hostname.
- Input order covers two staged files.
- Parallelism covers two independent compilations and one link step.
- Most variants also use distinct build paths; the path-only control bounds but does not erase that confounding.

## Self-review

- The complete final runner and workflow were inspected.
- The test asserts package, extracted payload, control, declared-epoch, parallel scheduling, and destructive-path contracts.
- The retained matrix and report distinguish `.deb` reproducibility from `.buildinfo`/`.changes` variance.
- Exact-head execution must be backed by named workflow runs; workflow presence alone is not a receipt.

## Reusable note

See `notes/packaging/isolating-debian-package-build-variance.md`.

## Promotion or stop decision

**Decision: `stop`.**

The first package difference is explained by a declared `SOURCE_DATE_EPOCH` change. The retained runner remains useful as a compact regression probe.

## Upstream authority state

No upstream contact was made or authorized.
