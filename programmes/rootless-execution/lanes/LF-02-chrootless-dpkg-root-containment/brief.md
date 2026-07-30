# LF-02 — Chrootless `DPKG_ROOT` Containment

## In simple words

Chrootless package installation asks dpkg and package scripts to act on a target directory while those scripts still execute in the host process environment. This lane tests whether package actions stay inside the intended target and whether unsafe packages fail before changing the host.

## Programme

[`Rootless execution, namespaces, and mounts`](../../STATUS.md)

## State

`active` — the `mmdebstrap` autopkgtest investigation is mapping the first failing case before any chrootless containment branch is promoted.

## Active work

- [`mmdebstrap` autopkgtest failure 1141078](../../../../investigations/mmdebstrap-autopkgtest-1141078/README.md) maps suite selection, package transitions, rootless execution, and the package test's chrootless cases.

## Question

Which maintainer-script operations escape the intended target when packages are installed through `DPKG_ROOT` or `--force-script-chrootless`?

## Why this could matter

A package may invoke host service actions, read host state as target state, or write outside the target. That crosses a direct host-integrity boundary.

## Likely targets

- imported `mmdebstrap` source;
- `dpkg` root-directory handling;
- Essential packages and debhelper-generated snippets;
- scripts invoking account, cache, service, boot, or path-discovery tools.

## First probe

Build a disposable target, trace filesystem writes and process execution, install a deliberately small package set in chrootless mode, and classify every access outside the target.

## Environment

Current CI inside an additional disposable container or nested root. Run the package action without host privileges where possible.

## Promotion signal

Promote into an investigation when a package writes outside the target, invokes a host service action, confuses host and target state, or leaves partial target configuration after a late failure.

## Stop signal

Close the scout when observed effects stay inside the declared target and required host reads are explicit and documented.

## Expected outputs

- source and call-path map;
- package fixture selection;
- write and process trace;
- candidate investigation path or retained negative result.

Create `artifacts/` only when evidence is retained.

## Authority

No upstream contact is authorized.
