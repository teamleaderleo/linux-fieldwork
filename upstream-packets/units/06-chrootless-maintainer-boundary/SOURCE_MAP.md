# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `mmdebstrap` | released/imported `6fde999741f4fe1e7bf38079acf29432ef87a35e`; current Salsa `master` unresolved | `run_essential()`, `run_install()`, `main()` and new chrootless helpers |
| Adjacent implementation | apt configuration handling in `mmdebstrap` | same | `DPkg::Path`, apt environment, `Dir::Bin::dpkg`, `DPkg::Options` |
| Upstream tests | `tests/chrootless`, `tests/chrootless-fakeroot` | imported `debian/1.5.7-3` | root-versus-chrootless archive/package comparison precedent |
| Build/package metadata | `debian/changelog`, `.perltidyrc` | imported `debian/1.5.7-3` | released identity and formatting authority |
| Contribution instructions | canonical Salsa project and Debian BTS | current destination review pending | controlled fork absent |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Classification |
| --- | --- | --- | --- |
| PR #22 | head `ce2ccfa75efef0ffb4b678e97633179c38e14ada`; run `30530666222`; artifact `8754537765`; digest `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b` | LF-02 credential/session inheritance and host-integration evidence | evidence |
| Issue #40 | open | environment threat boundary and required matrix | canonical issue |
| PR #57 | head `5ebb8095288c7b3c11a4d23e2a329d6424f6a96e`; merge `09e2c5ef74683723cca9cf70c1162dec0328750d` | unsafe-environment refusal and dpkg environment scrub | component |
| Issue #69 | closed completed | discovered host `/tmp` fallback after scrub | canonical finding |
| PR #73 | final reviewed head `4b07ce73ba46196ed7841abe5705c807418e0406` | narrow allowlist repair, superseded by stronger derived-path repair | superseded |
| PR #74 | merged into local history | derive, validate, create, mode, and pass target-local TMPDIR | component |
| Issue #107 | open | caller PATH and outer-wrapper authority findings | canonical issue |
| PR #109 | historical stacked candidate | first configured-`DPkg::Path` candidate and outer-wrapper review | superseded |
| Issue #337 | completed | current-main executable-authority restack | canonical composition issue |
| PR #368 | head `d776f908ac71b31f3c7c2ee068bc9e24bb816e17`; merge `8c83a739d9330418479a01bbef77d71bfc2dfbd7` | configured `DPkg::Path`, absolute env, direct/APT transactions, cleanup guards | canonical component |
| Linux Fieldwork main | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | packet branch base | canonical internal base |

## Candidate code

| File | Lines or symbols | Change | Owning patch |
| --- | --- | --- | --- |
| `mmdebstrap` | `chrootless_dpkg_environment` | construct small environment, target TMPDIR, configured PATH, preserved owned state | 0001–0003 |
| `mmdebstrap` | `chrootless_unsafe_environment` | detect credential/session names and URL userinfo | 0001 |
| `mmdebstrap` | `chrootless_env_path` | validate `/usr/bin/env` | 0004 |
| `mmdebstrap` | `run_essential` | absolute sanitizer plus explicit env for direct dpkg | 0001–0004 |
| `mmdebstrap` | `run_install` | apt-managed sanitizer argv and dpkg invocation | 0001–0004 |
| `mmdebstrap` | `main` | unsafe launch refusal and saved apt `DPkg::Path` | 0001, 0003 |
| `mmdebstrap` POD | chrootless and checks sections | precise defense-in-depth and override behavior | 0001, 0003 |

## Candidate tests

| File or carrier | Test or fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| PR #22 LF-02 fixture | fake credentials and agent socket | package sees values and connects | launch refusal or scrub blocks direct inheritance/socket path |
| PR #57 environment workflow | credential-rich apt-managed local package | values/session paths inherited | names-only refusal; apt auth retained; dpkg scrubbed |
| PR #74 target-TMPDIR fixture | postinst `mktemp` | `TMPDIR` unset and host `/tmp` used | exact `<target>/tmp`, mode 1777, cleanup |
| PR #368 APT transaction | fake caller `env`, `dpkg`, helper | fake executable wins under mutations | absolute outer env and configured inner PATH win |
| PR #368 direct transaction | direct Essential path argv/transaction | caller executable authority under mutations | same authority and package-set result as APT path |
| imported `tests/chrootless` | normalized root/chrootless comparison | compatibility discriminator | candidate preserves supported result |
| imported `tests/chrootless-fakeroot` | fakeroot comparison | compatibility discriminator | fakeroot state and result preserved |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-06-chrootless-maintainer-boundary`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS CURRENT-UPSTREAM CANDIDATE`
- Retained patch or series: `patches/series`
- Patch application command:

```sh
git checkout <exact-upstream-base>
git am /path/to/upstream-packets/units/06-chrootless-maintainer-boundary/patches/000*.patch
```

The current retained files are plain diffs rather than mail-formatted commits, so the first rebase worker may use `git apply` followed by review commits until headers are added:

```sh
while read -r patch; do git apply --check "patches/$patch" && git apply "patches/$patch"; done < patches/series
```

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| Reject credential-bearing launch | absent | mmdebstrap `main()` chrootless check | #40/#57 |
| Preserve apt repository/proxy environment | ambient apt invocation | unchanged apt invocation | #57 matrix |
| Build maintainer-script environment | caller environment | `chrootless_dpkg_environment` | #57 |
| Select package temporary directory | libc/tool fallback after scrub | validated `<target>/tmp` | #69/#74 |
| Select maintainer-script command path | caller-prefixed mmdebstrap PATH | apt configured non-empty `DPkg::Path` | #107/#337/#368 |
| Select outer sanitizer executable | caller PATH lookup of `env` | validated `/usr/bin/env` | #107/#368 |
| Direct Essential dpkg launch | `run_essential()` | same owner with explicit wrapper/env | #368 direct transaction |
| Apt-managed dpkg launch | apt `Dir::Bin::dpkg` | absolute env wrapper plus ordered options | #368 APT transaction |
| Recursive test cleanup | transaction harness | exact validated disposable target | #368 review-found repair |

## Overlap and current upstream state

Search date: 2026-08-01. The canonical repository is Salsa. Debian Sources and the package index expose released `1.5.7-3`, matching imported commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`. The exact current Salsa `master` commit and active issue/MR overlap remain unresolved because this execution environment could read the project page but could not retrieve the branch API or raw master content. No assumption that released source equals current master is made.

## Files deliberately not changed

- `upstream/mmdebstrap/mmdebstrap` remains untouched on this packet branch; upstream product work is retained as patches.
- Shared transaction harnesses and classifiers from PR #368 remain canonical in their landed locations instead of being copied into the packet.
- Host setup-hook command lookup remains outside this unit because it has a different operation owner.
- Non-chrootless modes remain outside the product patch except as regression controls.