# Chrootless executable and PATH authority on current main

State: `current-main composition prepared — exact-head execution pending`

## TL;DR

Current `mmdebstrap` chrootless mode has two connected executable-authority defects:

1. the outer sanitizer is found as bare `env` through caller-controlled `PATH` before `env -i` can sanitize anything;
2. the sanitized maintainer-script environment then copies that same caller `PATH` inside the boundary.

This carrier keeps the two corrections separate and composes them in order:

- patch 0001 installs apt's configured non-empty `DPkg::Path` inside the clean environment for direct and apt-managed chrootless paths;
- patch 0002 validates and invokes `/usr/bin/env` as the outer wrapper for both paths.

## Explain like I'm five

The program asks an untrusted street directory to find the guard who will replace the street directory. After the guard starts, it also hands package scripts the old directory.

The repair names the guard directly, then gives package scripts the path configured by the package manager.

## Why care

A fake `env` found before sanitization can inspect or change the launch and restore unsafe command lookup. A fake inner command found after sanitization can run in place of `dpkg` or a maintainer-script helper.

The direct `run_essential()` path and apt-managed `run_install()` path use different wrapper surfaces, so both need the same outer and inner authority.

## Current source boundary

The imported current-main source:

- lists `PATH` among values copied from the caller into `env -i`;
- emits only target-derived `TMPDIR` as a program-owned clean value;
- invokes bare `env` in direct chrootless `ARGV`;
- configures `Dir::Bin::dpkg=env` for apt-managed chrootless installation;
- reads apt's `DPkg::Path` only to augment mmdebstrap's own host-side PATH.

The imported source is not modified in this repository. The carrier retains two patches and applies them to a disposable copy.

## Patch 0001 — configured inner PATH

`0001-use-configured-dpkg-path.patch`:

- records apt's configured `DPkg::Path` in the options object;
- passes it into both direct and apt-managed chrootless launch paths;
- rejects undefined or empty configured path before maintainer-script execution;
- removes caller `PATH` from the copied environment list;
- emits `PATH=$dpkgpath` beside target-derived `TMPDIR`;
- preserves debconf, locale, reproducibility, QEMU, and fakeroot state;
- updates the chrootless documentation to name the configured authority.

## Patch 0002 — absolute outer wrapper

`0002-use-absolute-env-wrapper.patch`:

- names `/usr/bin/env` explicitly;
- requires the wrapper to exist, be a regular file, and be executable;
- uses the helper in direct chrootless `ARGV`;
- uses the same helper as apt's `Dir::Bin::dpkg` wrapper;
- does not change non-chrootless apt behavior.

The explicit path is a compatibility decision for the supported Debian/Linux execution environment. The fixture does not claim every Unix-like platform provides `/usr/bin/env`.

## Cross-context review receipt

- **outer versus inner lookup** — separate patches and separate controls;
- **direct versus apt-managed path** — both call sites assert the same helper and configured PATH;
- **caller state versus program state** — fake leading-path wrapper and fake inner helper are distinguishing controls;
- **empty configuration** — candidate fails before constructing the clean environment;
- **wrapper object identity** — missing, directory, non-executable, and executable cases execute the exact helper body;
- **retained patch identity** — both patches must apply with zero fuzz to the imported current source;
- **complete source** — the composed disposable source must pass `perl -c`.

No selected context changes the two-layer design. Full dpkg and apt transactions remain the next promotion gate.

## Executable regression

`tests/test_mmdebstrap_chrootless_env_authority_composition.py` requires:

1. exact zero-fuzz application of patch 0001 and patch 0002;
2. complete Perl syntax after composition;
3. source ownership at both direct and apt-managed call sites;
4. no caller `PATH` in the clean environment list;
5. configured `PATH=$dpkgpath` in the clean environment;
6. a fake leading-path `env` intercepts the baseline spelling;
7. `/usr/bin/env` bypasses that fake wrapper under the same inherited environment;
8. a caller-selected inner helper runs under caller PATH;
9. the configured inner path selects the program-owned helper instead;
10. the exact `chrootless_env_path()` body rejects missing, non-regular, and non-executable paths and accepts an executable regular file.

The fake wrapper delegates to `/usr/bin/env`, so the baseline control demonstrates interception without breaking the reduced command.

## Evidence boundary

This carrier proves patch composition, source-shape ownership, general executable-search behavior, and the exact wrapper validator in reduced disposable controls.

It does not yet execute:

- a complete direct essential package transaction;
- apt-managed package installation;
- a real maintainer script;
- an explicit `APT_CONFIG` transaction;
- credential, proxy, formatter, TMPDIR, fakeroot, or architecture workflows on the composed head;
- wrapper replacement races after validation;
- non-Debian filesystem layouts.

Those surrounding workflows are required before a production recommendation. A green repository gate is not a substitute for the transaction matrix.

## History and intent

PR #109 retained the canonical inner-PATH source direction and the absolute-wrapper patch, but its branch became 172 main commits stale and mixed component evidence with old delivery history. Issue #337 owns this clean current-main composition rather than restacking that history wholesale.

The design follows the existing apt-configured `DPkg::Path` authority and the broader rule that a sanitizer must not be located through the state it intends to sanitize.

## Disposition

`COMPOSE AND EXECUTE REDUCED AUTHORITY GATE`.

If the exact carrier passes, retain it as the bounded current-main source unit and then add the direct and apt-managed fake-outer-wrapper transaction matrix on the same technical patches. Do not promote the reduced controls to full product compatibility evidence.

Internal Linux Fieldwork work only. No Debian or external contact is authorized or included.

Refs #337, #109, #107, #105, merged environment hardening #57, and target TMPDIR #74.
