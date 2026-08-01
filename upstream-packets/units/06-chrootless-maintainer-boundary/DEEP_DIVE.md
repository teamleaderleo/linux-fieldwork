# Deep dive

## Question and observed failure

The bounded question is: what environment and executable authority should mmdebstrap give package maintainer scripts when `--mode=chrootless` deliberately runs them as host processes?

Four distinguishing failures were established in sequence:

1. LF-02 showed caller credentials, session endpoints, and a fake agent socket reaching a package script.
2. Clearing the environment without assigning `TMPDIR` made ordinary temporary helpers write below host `/tmp`.
3. Copying mmdebstrap's caller-prefixed PATH into the scrubbed environment let a package script execute a caller-controlled command.
4. Naming `env` through PATH let a caller-controlled outer wrapper execute before the canonical inner PATH assignment became effective.

The source owner is mmdebstrap's chrootless dpkg launch boundary. Apt repository access remains a separate outer operation and keeps its existing environment.

## Source mechanism

`main()` obtains apt's `DPkg::Path` and also extends mmdebstrap's own host-side PATH for tool discovery. The original chrootless paths inherited that ambient state:

- `run_essential()` invokes dpkg directly for Essential packages;
- `run_install()` asks apt to invoke dpkg through `Dir::Bin::dpkg` and ordered `DPkg::Options`.

The selected correction introduces three explicit helper responsibilities:

- `chrootless_unsafe_environment()` classifies launch-time variable names and credential-bearing URL userinfo;
- `chrootless_dpkg_environment($root, $dpkgpath)` validates target temporary state and returns the exact `env -i` argument vector;
- `chrootless_env_path()` validates and returns `/usr/bin/env`.

Both call sites consume the same environment helper, so direct and apt-managed package execution share one contract.

## Reproduction narrative

LF-02 builds a purpose-made package whose maintainer script records selected environment names and connects to a fake local socket. The baseline exposed fake credentials and delivered a canary to the socket.

The target-TMPDIR fixture uses `mktemp` in `postinst`. After the first scrub, the script observed `TMPDIR=<unset>` and created `/tmp/lf-chrootless-tmp.*`. The selected repair requires exact `<target>/tmp`, mode 1777, contained creation, removal, and clean rerun.

The executable-authority fixtures place harmless fake `env`, `dpkg`, and helper commands at the front of caller PATH. Candidate runs bypass them. Separate losing mutations restore caller PATH to the inner environment or restore bare `env`; each mutation must execute the corresponding fake command.

Full commands and receipts remain in `TESTS.md` and the linked carriers.

## Approach history

### Approach A — ambient caller environment

- mechanism: inherited apt/mmdebstrap process environment reaches dpkg and scripts;
- evidence: LF-02 credential values and fake agent connection;
- result: rejected;
- compatibility cost: none, with direct credential/session exposure;
- disposition: superseded.

### Approach B — launch refusal plus dpkg-only `env -i`

- mechanism: reject high-risk names unless explicitly skipped; keep apt ambient state; scrub only dpkg/script boundary;
- evidence: PR #57 security matrix and artifact;
- result: blocks tested direct inheritance and socket path while preserving apt proxy/auth state;
- compatibility cost: requires an explicit allowlist and precise override wording;
- disposition: accepted as the base correction.

### Approach C — remove TMPDIR with the caller environment

- mechanism: omit arbitrary caller TMPDIR from the allowlist;
- evidence: issue #69 package `mktemp` probe;
- result: selects host `/tmp` through ordinary fallback;
- compatibility cost: writes outside the selected target;
- disposition: rejected.

### Approach D — pass the already-normalized ambient TMPDIR

- mechanism: add current `%ENV{TMPDIR}` to the allowlist after `run_setup()` rewrites it;
- evidence: PR #73 exact-target assertions;
- result: narrow repair works on that lifecycle;
- compatibility cost: relies on distant setup ordering and leaves helper responsibility implicit;
- disposition: superseded by derived-path validation.

### Approach E — derive and validate `<target>/tmp` at the dpkg boundary

- mechanism: helper receives the selected root, rejects symlink/non-directory, creates when absent, enforces 01777, and emits exact TMPDIR;
- evidence: PR #74 mutation, fakeroot, cleanup, rerun;
- result: accepted;
- compatibility cost: chrootless package execution now fails closed on unsafe target temporary paths;
- disposition: selected.

### Approach F — preserve caller-prefixed PATH inside `env -i`

- mechanism: copy mmdebstrap's current PATH into the small environment;
- evidence: issue #107 fake caller command;
- result: package script resolves caller-controlled executable;
- compatibility cost: nondeterministic command authority;
- disposition: rejected.

### Approach G — filter individual PATH components

- mechanism: inspect ownership/writability and retain apparently safe entries;
- evidence: precedent review in PR #105;
- result: policy ambiguity and check/use races;
- compatibility cost: machine-dependent command set;
- disposition: rejected.

### Approach H — apt configured `DPkg::Path`

- mechanism: save apt's configured value before extending mmdebstrap's own PATH; require non-empty; pass it to both chrootless dpkg paths;
- evidence: #107/#337 and PR #368 direct/APT transactions, inner mutation, expected tool resolution;
- result: accepted;
- compatibility cost: an explicitly empty `DPkg::Path` fails closed instead of inheriting caller PATH;
- disposition: selected and documented.

### Approach I — bare `env` with canonical inner PATH

- mechanism: resolve sanitizer through caller PATH, then assign canonical PATH;
- evidence: independent outer-wrapper review and fake leading-path env;
- result: fake outer program runs before sanitization;
- compatibility cost: defeats executable authority at the first hop;
- disposition: rejected.

### Approach J — validated absolute `/usr/bin/env`

- mechanism: require existing regular executable `/usr/bin/env`; use it directly in both paths;
- evidence: PR #368 outer mutation and transaction receipts;
- result: accepted for the Debian/Linux platform premise;
- compatibility cost: non-Debian layouts need a separate portability decision;
- disposition: selected.

## Selected correction

Retain four ordered patches:

1. launch refusal, names-only reporting, dpkg-only explicit environment, and precise documentation;
2. target-derived validated `TMPDIR`;
3. apt-configured non-empty maintainer-script PATH;
4. validated absolute sanitizer executable.

The series should be rebased as a unit onto exact current Salsa master, preserving reviewable commits and testing only the complete final state for promotion.

## Why the changes belong together

All four patches govern the same transition from apt/mmdebstrap host process to chrootless dpkg and package script. Each intermediate state has a demonstrated defect:

- scrub absent: credentials/session endpoints pass through;
- scrub without target TMPDIR: host `/tmp` becomes default;
- scrub with caller PATH: inner executable authority remains caller-controlled;
- canonical inner PATH with bare env: outer executable authority remains caller-controlled.

The helper and both call sites overlap. One upstream series avoids shipping a knowingly incomplete boundary while preserving commit-by-commit explanation.

## Compatibility analysis

### Environment and command lookup

Apt keeps its environment for proxy, repository authentication, and host-side behavior. Dpkg/scripts receive only mmdebstrap-owned values: target TMPDIR, configured PATH, noninteractive debconf values, forced C.UTF-8 locale values, TZ and SOURCE_DATE_EPOCH when set, QEMU_LD_PREFIX when active, and fakeroot variables when active.

### Files and cleanup

`<target>/tmp` must be a real directory, is created when absent, and is forced to mode 01777. Symlink and non-directory targets fail closed. Test-created temporary paths are removed and rerun checks prove no residue within the fixture premise.

### Process and socket boundary

The tested fake agent socket receives no package-script connection after launch refusal/scrub. Package scripts still run on the host and retain same-user access available through other process, filesystem, and socket discovery paths.

### Supported platforms and modes

The selected outer path assumes Debian/Linux `/usr/bin/env`. Direct Essential and apt-managed chrootless paths are covered by PR #368. Non-chrootless apt behavior remains unchanged. Fakeroot and QEMU state are preserved by the explicit environment when active, with broader combination coverage still pending on current upstream.

## Negative controls and losing mutations

- ambient direct dpkg control exposes fake credentials and connects to the fake socket;
- removing target TMPDIR assignment yields `TMPDIR=<unset>` and host `/tmp` creation;
- restoring caller PATH to the small environment executes fake inner dpkg/helper;
- restoring bare `env` executes the fake outer sanitizer;
- explicit empty `DPkg::Path` fails before script execution;
- cleanup guards reject repository/HOME overlap and unsafe runtime identities.

## Current upstream and historical review

Released Debian source `1.5.7-3` resolves to commit `6fde999741f4fe1e7bf38079acf29432ef87a35e` and remains the exact imported source basis. The current Salsa project page was reachable on 2026-08-01, while branch API/raw master retrieval failed in this execution environment. The packet therefore records current master as unresolved and avoids claiming zero-fuzz application there.

No upstream discussion or overlap was opened. Active Salsa issue/MR search remains an explicit pre-submission gate.

## Remaining questions

1. **Current base identity:** fetch exact Salsa master commit and `mmdebstrap` blob. Discriminator: canonical branch API or a verified clone.
2. **Series application:** run ordered `git apply --check`/`git am` with zero fuzz. Discriminator: exact command output and final diff review.
3. **Complete final-state matrix:** run direct and apt-managed fixtures with all four patches together. Discriminator: candidate and each losing mutation produce the expected distinct records.
4. **Native compatibility:** run current `tests/chrootless`, `tests/chrootless-fakeroot`, formatting, syntax, and relevant package gates. Discriminator: exact current candidate head results.
5. **Overlap:** search current Salsa issues/MRs and Debian BTS. Discriminator: recorded references and adoption decision.

## Evidence boundary

Existing evidence establishes the components and the composed executable-authority pair on Linux Fieldwork's imported Debian source and hosted Debian runners. It does not establish current Salsa master application, every secret representation, every proxy/auth combination, every fakeroot/QEMU combination, non-Debian `/usr/bin/env` layout, or a package-script sandbox.

## Reopen triggers

- current upstream already implements an equivalent boundary;
- helper/call-site topology changes;
- apt changes `DPkg::Path` semantics;
- Debian changes the `/usr/bin/env` platform contract;
- a required maintainer-script state variable is proven missing;
- a benign environment name creates unacceptable detector false positives;
- a counterexample defeats target TMPDIR or executable authority inside the tested premises;
- external authorization or destination changes.