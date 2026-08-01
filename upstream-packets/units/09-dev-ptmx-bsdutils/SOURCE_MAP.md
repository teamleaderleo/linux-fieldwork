# Source map

## Upstream source

| Role | Identity |
| --- | --- |
| Canonical repository | `josch/mmdebstrap` on `gitlab.mister-muffin.de` |
| Intended base branch | `main` |
| Advertised base head | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Owning file | `tests/dev-ptmx` |
| Owning line | generated-root `--include=` declaration |
| Command used in root | `/usr/bin/script` |
| Provider | Debian package `bsdutils` |
| Delivery | Forgejo fork and pull request; `NEEDS FORK` |

## Linux Fieldwork source and candidate

| Role | Path or identity |
| --- | --- |
| Imported baseline | `upstream/mmdebstrap/tests/dev-ptmx` |
| Imported blob | `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` |
| Existing internal patch | `investigations/mmdebstrap-dev-ptmx-bsdutils/0001-include-bsdutils.patch` |
| Upstream-path packet patch | `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch` |
| Historical evidence | `investigations/mmdebstrap-dev-ptmx-bsdutils/debci-72574145-summary.json` |
| Regression | `tests/test_mmdebstrap_dev_ptmx_dependency.py` |
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

## Historical artifact identity

- Debian CI run: `72574145`
- Capture workflow: `30538316641`
- Artifact: `debci-mmdebstrap-72574145-capture-2`
- Artifact digest: `sha256:9e9ded80793210b59ff34398e7d78a6e33be2723515b77eee26e9b40fc5a138a`
- Compressed log: `222237` bytes
- Decompressed log: `1713654` bytes
- Artifact tar: `4097` bytes

## Ownership boundary

This unit changes a package-test fixture dependency. It leaves mmdebstrap runtime code, util-linux packaging, mirror readiness, non-Debian suite classification, subordinate-ID matching, signal behavior, and broad current-sid phase ordering untouched.
