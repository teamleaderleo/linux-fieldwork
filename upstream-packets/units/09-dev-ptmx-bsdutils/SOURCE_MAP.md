# Source map

## Canonical upstream source

| Role | Identity |
| --- | --- |
| Canonical repository | `josch/mmdebstrap` on `gitlab.mister-muffin.de` |
| Intended base branch | `main` |
| Advertised base head | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Owning file | `tests/dev-ptmx` |
| Owning line | generated-root `--include=` declaration |
| Command used in root | `/usr/bin/script` |
| Provider | Debian package `bsdutils` |
| Final delivery | Canonical Forgejo fork and pull request after authorization |

## Controlled GitHub implementation carrier

| Role | Identity |
| --- | --- |
| Repository | `teamleaderleo/mmdebstrap` |
| Provenance | GitHub fork of `deepin-community/mmdebstrap` |
| Downstream base branch | `master` |
| Downstream base head | `574048f2a720057b75e56622003932f344dc700a` |
| Base commit subject | `feat: update mmdebstrap to 1.5.7-3` |
| Base source blob | `tests/dev-ptmx` at `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Candidate branch | `linux-fieldwork/unit-09-dev-ptmx-bsdutils` |
| Candidate head | `43082a6bc959e2d7cefae48f52e045cc90869287` |
| Candidate blob | `tests/dev-ptmx` at `fa93b4b845ff4927a72f258364bd920e8c7dc573` |
| Candidate compare | one commit; one file; one insertion; one deletion |
| Pull request | none; branch only |

This carrier is suitable for the Debian `1.5.7-3` package-source case. It is not canonical mmdebstrap ancestry and cannot prove inclusion of later Forgejo or mailing-list-carried patches.

## Linux Fieldwork source and candidate

| Role | Path or identity |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-09-dev-ptmx-bsdutils` |
| Internal validation PR | draft `#402` |
| Imported baseline | `upstream/mmdebstrap/tests/dev-ptmx` |
| Imported blob | `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Existing internal patch | `investigations/mmdebstrap-dev-ptmx-bsdutils/0001-include-bsdutils.patch` |
| Upstream-path packet patch | `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch` |
| Historical evidence | `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json` |
| Original regression | `tests/test_mmdebstrap_dev_ptmx_dependency.py` |
| Packet/fork regression | `tests/test_upstream_packet_unit_09_dev_ptmx_bsdutils.py` |
| Reusable lesson | `notes/debian/tests-must-declare-command-providers-not-essential-set-assumptions.md` |

## Carrier chain read

- Issue `#397`: canonical unit boundary and packet protocol.
- Issue `#53`: central investigation, recovered run identity, owner, and separated follow-on defects.
- PR `#82`: disposable immutable Debian CI capture; closed without merge.
- Issue `#84`: focused source boundary and regression requirement.
- PR `#86`: first focused candidate; closed after divergent history was superseded.
- PR `#89`: clean current-main promotion; merged into Linux Fieldwork at `96f344e708279d246ea19fdea93a9f8b7a4ff4a6`.
- PR `#60`: durable transition dossier and classifier; historical ownership agrees with this unit.
- PR `#72`: reusable current-sid disposable execution carrier; its later phase-scope defects are separate from unit 09.
- Unit `08` packet: current distilled Debian `1.5.7-3` package-test series and exact executable base `debian/1.5.7-3` at `6fde999741f4fe1e7bf38079acf29432ef87a35e`.
- Draft PR `#402`: internal CI activation for the unit-09 packet regression.

## Historical artifact identity

- Debian CI run: `72574145`
- Capture workflow: `30538316641`
- Artifact: `debci-mmdebstrap-72574145-capture-2`
- Artifact digest: `sha256:9e9ded80793210b59ff34398e7d78a6e33be2723515b77eee26e9b40fc5a138a`
- Compressed log: `222237` bytes
- Decompressed log: `1713654` bytes
- Artifact tar: `4097` bytes

## Ownership boundary

This unit changes a package-test fixture dependency. It leaves mmdebstrap runtime code, util-linux packaging, mirror readiness, non-Debian suite classification, subordinate-ID matching, signal behavior, broad current-sid phase ordering, Deepin packaging changes, and unrelated mailing-list patches untouched.
