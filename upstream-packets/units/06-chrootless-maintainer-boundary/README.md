# Unit 06 — mmdebstrap chrootless maintainer-script boundary hardening

State: `ACTIVE`  
Priority-zero issue: #397, unit 06  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-06-chrootless-maintainer-boundary`  
External contact authorized: `false`

## TL;DR

The complete product boundary consists of four ordered corrections: reject credential-bearing launches and scrub the dpkg environment; derive package temporaries below `<target>/tmp`; use apt's configured non-empty `DPkg::Path` for maintainer-script command lookup; and invoke the sanitizer through validated `/usr/bin/env`. Linux Fieldwork has exact passing evidence for each component and for the composed executable-authority pair.

A controlled GitHub mirror now exists at `teamleaderleo/mmdebstrap`. Its `master` tip is `574048f2a720057b75e56622003932f344dc700a`, carrying mmdebstrap `1.5.7-3`, and its `mmdebstrap` source blob is `075582e1ca9cf50a1be497105ba77c82345c2bf3`. Candidate branch `linux-fieldwork/unit-06-chrootless-maintainer-boundary` was created from that exact tip. The mirror resolves the candidate-hosting blocker. It remains a mirror rather than a direct Salsa fork, so final delivery still needs a later destination decision and explicit authorization.

## Accomplished behavior

Chrootless package execution rejects commonly credential-bearing caller environments unless the dedicated risk override is supplied. Apt keeps its caller environment for repository and proxy compatibility, while both direct Essential installation and apt-managed dpkg execute with a small explicit environment. Package temporary files use a validated target-local directory, maintainer-script command lookup uses apt's configured non-empty `DPkg::Path`, and the outer environment sanitizer is the validated absolute `/usr/bin/env` executable.

## Why care

Caller credentials and session sockets reached chrootless maintainer scripts in LF-02. The first sanitizer candidate then sent ordinary package temporaries to host `/tmp`. A later review proved that caller-prefixed `PATH` could select both an unintended maintainer-script helper and a fake outer `env` before sanitization began. These are one operation boundary: the host-side launch of package maintainer scripts in chrootless mode.

## Scope

### Included

- launch-time detection of credential-like variables, credential-file pointers, session endpoints, and credential-bearing URLs;
- explicit dpkg/maintainer-script environment construction for both direct and apt-managed chrootless paths;
- validated `<target>/tmp` creation and `TMPDIR` assignment;
- apt-configured non-empty `DPkg::Path` as maintainer-script `PATH`;
- validated absolute `/usr/bin/env` as the outer sanitizer;
- preservation of mmdebstrap-owned debconf/locale values, reproducibility state, QEMU state, and conditional fakeroot state;
- documentation of the remaining host-execution boundary.

### Excluded

- sandboxing package scripts;
- host setup-hook command lookup;
- non-chrootless execution changes;
- broad preservation of arbitrary caller locale or `DEBCONF_*` variables;
- every possible secret-name representation;
- external submission or discussion.

### Split boundary

The four corrections overlap the same helper and its two call sites. Splitting environment scrubbing from target `TMPDIR`, inner command authority, or outer wrapper authority would create intermediate regressions already demonstrated by the carrier history. Review may still use four ordered commits, but the submission unit should preserve the complete invariant.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://salsa.debian.org/debian/mmdebstrap` |
| Intended base branch | `master` |
| Canonical Salsa base commit | unresolved in this runtime |
| Released/imported base | `6fde999741f4fe1e7bf38079acf29432ef87a35e` (`debian/1.5.7-3`) |
| Controlled mirror | `https://github.com/teamleaderleo/mmdebstrap` |
| Mirror base branch | `master` |
| Mirror base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Mirror source blob | `075582e1ca9cf50a1be497105ba77c82345c2bf3` (`mmdebstrap`) |
| Candidate source branch | `linux-fieldwork/unit-06-chrootless-maintainer-boundary` |
| Candidate head | currently equal to mirror base pending patch application |
| Linux Fieldwork branch | `upstream/unit-06-chrootless-maintainer-boundary` |
| Linux Fieldwork head | see `HANDOFF.md` |
| Imported/local post-component source identity | blob `41aa46f989a2660cebdb0138e0847cde25b269a3` at Linux Fieldwork `main` `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Patch or series path | `patches/series` |
| Proposed destination | Debian/mmdebstrap canonical Salsa repository |
| Delivery method | `NEEDS DESTINATION DECISION`; likely Salsa merge request or patch series |

## Canonical links

- Priority-zero unit: #397 unit 06
- Owning Linux Fieldwork issues: #40, #69, #107, #337
- Canonical Linux Fieldwork compositions: PR #57, PR #74, PR #368
- Evidence predecessor: PR #22 (LF-02)
- Superseded/intermediate carriers: PR #73, PR #109, PR #349
- Controlled mirror: `teamleaderleo/mmdebstrap`
- Candidate mirror branch: `linux-fieldwork/unit-06-chrootless-maintainer-boundary`
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- LF-02 showed direct caller credential/session inheritance and fake agent-socket use.
- PR #57 rejected tested unsafe launch variables, redacted fake values, kept apt proxy/auth state at apt, scrubbed apt-managed dpkg, preserved selected required state, and blocked the fake agent socket.
- PR #74 kept package `mktemp` below target `tmp`, enforced mode `01777`, rejected symlink/non-directory targets, cleaned up, reran, and passed fakeroot.
- PR #368 proved configured `DPkg::Path` and absolute `/usr/bin/env` for direct and apt-managed paths with losing mutations and equal installed package sets.
- The controlled mirror exposes an exact released-source base and a writable candidate branch.
- The mirror base source is pre-hardening at the relevant boundary: `run_essential()` follows `run_prepare()` directly and has no `chrootless_dpkg_environment` helper at the inspected source range.

### Not yet demonstrated

- ordered four-patch application on mirror commit `574048f2a720057b75e56622003932f344dc700a`;
- exact candidate head after application;
- direct and apt-managed transactions with the complete detector, temporary-directory, inner-PATH, and outer-wrapper matrix on the mirror candidate;
- mirror-candidate formatting and relevant native tests;
- exact relation between the mirror base and current canonical Salsa `master`;
- active-overlap search on current Salsa issues and merge requests.

### Compatibility boundary

The supported dpkg environment is mmdebstrap-owned state: noninteractive debconf controls, forced C.UTF-8 locale values, target-local `TMPDIR`, reproducibility controls, QEMU state, and fakeroot state when active. Apt itself retains its environment. Chrootless maintainer scripts continue to execute as host processes with same-user host access.

## Candidate organization

1. `0001-sanitize-chrootless-maintainer-environment.patch`
2. `0002-use-target-contained-tmpdir.patch`
3. `0003-use-configured-dpkg-path.patch`
4. `0004-use-absolute-env-wrapper.patch`

These commits form one coherent invariant while keeping review history legible. Each later patch closes a concrete defect in the preceding intermediate state.

## Current disposition

`ACTIVE` — controlled candidate hosting exists; patch application and complete candidate gates remain.

## Next human decision

No additional setup is required from the repository owner. Technical application and validation come next. A later decision will authorize or hold external submission after the packet reaches `READY FOR AUTHORIZATION`.

## Authority

Internal repository reads, branch creation, packet commits, patch composition, tests, and issue checkpoints are authorized. No Debian or mmdebstrap issue, merge request, email, comment, review, release, or other external contact has been authorized or made.