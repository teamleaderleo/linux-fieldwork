# Source map

## Canonical ownership

| Role | Identity |
| --- | --- |
| Repository | `josch/mmdebstrap` on Muffin Forgejo |
| Stable branch inspected | `main` at `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Development branch inspected | `develop` at `6e1e572bc49456daab7fd1274b1f3b8ec4a1c248` |
| Owning file | `tests/dev-ptmx` |
| Baseline blob on `main` | `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Corrected blob on `develop` | `258a7f9579b2a2b91b6758952851296b44197ae0` |
| Owning commit | `c75b58e3c88b1f49626b9ee073e9e9688d38922c` |
| Commit subject | `make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility` |
| Author date | `2025-11-16T00:04:44+01:00` |
| Corrected tag | `1.5.7+develop` |
| Command used in root | `/usr/bin/script` |
| Provider | Debian package `bsdutils` |
| Delivery disposition | already implemented; no new submission |

Canonical branch distinction:

```text
main:    --include=gcc,libc6-dev,python3,passwd
develop: --include=gcc,libc6-dev,python3,passwd,bsdutils
```

## Read-only canonical audit

| Role | Identity |
| --- | --- |
| Linux Fieldwork audit PR | `#411` |
| Audit branch | `investigation/mmdebstrap-canonical-audit-unit09` |
| Audit carrier head | `8c8b8a1753881b86f1d5628be659a98fbcc02c6f` |
| Workflow run | `30704384974` |
| Job | `91380861751` |
| Artifact | `8819850852` |
| Artifact digest | `sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b` |
| Durable receipt | `artifacts/CANONICAL-FORGEJO-AUDIT.md` |

The audit used mirror clones and inspected all advertised refs and full path history. Broad issue and mailing-list term counts were noisy; canonical Git history supplied the decisive exact successor.

## Controlled downstream implementation carrier

| Role | Identity |
| --- | --- |
| Repository | `teamleaderleo/mmdebstrap` |
| Provenance | fork of `deepin-community/mmdebstrap` |
| Downstream base | `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Base generation | Debian `mmdebstrap 1.5.7-3` |
| Base blob | `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Candidate branch | `linux-fieldwork/unit-09-dev-ptmx-bsdutils` |
| Candidate head | `43082a6bc959e2d7cefae48f52e045cc90869287` |
| Candidate blob | `fa93b4b845ff4927a72f258364bd920e8c7dc573` |
| Compare | one commit; one file; one insertion; one deletion |
| Pull request | none |
| Final role | historical execution evidence only |

The downstream fork omitted later canonical `develop` history. Its candidate placed `bsdutils` first; canonical appends it. The package set is equivalent, and canonical ordering owns the final source.

## Linux Fieldwork packet

| Role | Path or identity |
| --- | --- |
| Branch | `upstream/unit-09-dev-ptmx-bsdutils` |
| Packet | `upstream-packets/units/09-dev-ptmx-bsdutils/` |
| Imported baseline | `upstream/mmdebstrap/tests/dev-ptmx` |
| Imported blob | `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Retained upstream-path patch | `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch` |
| Historical evidence | `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json` |
| Original regression | `tests/test_mmdebstrap_dev_ptmx_dependency.py` |
| Packet regression | `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py` |
| Dynamic receipt | `artifacts/CURRENT-SID-DOUBLE-PASS.md` |
| Canonical receipt | `artifacts/CANONICAL-FORGEJO-AUDIT.md` |

## Carrier chain

- Issue `#397`: unit boundary and packet protocol.
- Issue `#53`: recovered Debian CI owner and separated follow-ons.
- PR `#82`: immutable Debian CI capture.
- Issue `#84`: focused dependency boundary.
- PRs `#86` and `#89`: initial and clean Linux Fieldwork candidates.
- PR `#60`: transition dossier.
- PR `#72` and unit `08`: reusable current-sid package-test carriers.
- PR `#402`: packet static validation.
- PR `#403`: superseded full-cache dynamic carrier; retained two positive artifacts.
- PR `#407`: optional direct dynamic carrier; no longer required.
- PR `#411`: read-only canonical audit that found the existing upstream successor.

## Ownership boundary

The unit concerns one package-test fixture dependency. Runtime code, util-linux packaging, mirror readiness, subordinate-ID matching, signal behavior, broad current-sid phase ordering, and unrelated canonical development remain outside this unit.
