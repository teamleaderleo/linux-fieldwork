# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | released/imported `6fde999741f4fe1e7bf38079acf29432ef87a35e`; current Salsa `master` unresolved |
| Mirror base | `teamleaderleo/mmdebstrap` `master` at `574048f2a720057b75e56622003932f344dc700a` |
| Candidate head | mirror candidate branch exists but still equals base; four-patch application pending |
| Linux Fieldwork head | see `HANDOFF.md` |
| Platform/distribution | inherited carrier runs: GitHub-hosted Debian/current sid and Ubuntu 24.04; new dpkg probe: isolated Linux task runtime |
| Architecture | inherited carriers primarily amd64; new probe x86_64 |
| Privilege boundary | unprivileged chrootless, fakeroot, dedicated privileged LF-02 controls, and one root-only disposable system-config probe |
| Important tool versions | new probe: dpkg `1.22.22`; carrier versions retained in linked artifacts |

## Evidence classification for this pass

This pass executed a focused dpkg configuration-isolation probe with a synthetic package and disposable target roots. The probe temporarily created one uniquely named file below `/etc/dpkg/dpkg.cfg.d` inside the isolated task runtime, removed it through the ordinary path and trap fallback, and verified its absence before exit. It did not execute mmdebstrap or apply the four-patch candidate.

Runtime results inherited from linked carriers remain labeled with exact run and artifact identities.

## Baseline reproducer

### Command

Canonical mmdebstrap commands live in PR #22, PR #57, PR #74, and PR #368 transaction scripts. The mirror-baseline command remains to be adapted after the four-patch candidate is created.

### Expected distinguishing result

Released source without the series exposes ambient environment inheritance, caller executable authority, and no product-level target-TMPDIR helper. Independently, host dpkg configuration remains active because dpkg reads it outside the package-script environment construction.

### Observed result

- LF-02 run `30530666222`, job `90831976076`, artifact `8754537765`, digest `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b`;
- fake credentials/session variables reached the package script;
- the package script connected to a fake agent socket and sent a canary;
- Ubuntu host `/usr/lib/needrestart/dpkg-status` executed during a root chrootless target transaction;
- host file `/run/needrestart/unpacked` was created and restored by the disposable runner;
- disabling the host needrestart dpkg fragment removed that execution and mutation.

## Four-patch candidate reproducer

### Application command

```sh
while read -r patch; do
    git apply --check "/path/to/unit/patches/$patch"
    git apply "/path/to/unit/patches/$patch"
done < /path/to/unit/patches/series
```

Then run the landed direct and APT-managed transaction harnesses against that exact candidate copy, followed by upstream-native gates.

### Expected result

- credential-rich launch rejected with names only;
- override bypasses only the launch refusal while dpkg remains scrubbed;
- apt proxy/auth state remains visible to apt and absent from package scripts;
- direct and apt-managed script environments use configured `DPkg::Path`, target-local `TMPDIR`, and absolute `/usr/bin/env`;
- fake outer env, fake inner dpkg/helper, and host `/tmp` mutations each lose only under the corresponding candidate correction;
- expected package state and cleanup survive immediate rerun.

### Observed result

Mirror candidate: `NOT RUN`; branch still equals mirror base.

## Dpkg configuration-isolation probe

### Command

```sh
sudo upstream-packets/units/06-chrootless-maintainer-boundary/scripts/run-dpkg-config-probe.sh \
  | tee upstream-packets/units/06-chrootless-maintainer-boundary/artifacts/dpkg-config-probe.txt
```

### Exact identities

- runner: `scripts/run-dpkg-config-probe.sh`;
- receipt: `artifacts/dpkg-config-probe.txt`;
- runner SHA-256: `f5c73af6112006f79eb738438143deb4776a741aefac17d5850c0b6da0337edc`;
- receipt SHA-256: `ebc5df68f37350ea973fb5dbec39875cf1578a27dad88fa6dca2f1a2b72ebf76`;
- dpkg: `1.22.22`;
- synthetic package: `lf-dpkg-config-probe` version `1.0`;
- package paths: `/opt/lfprobe/keep` and `/usr/share/doc/lfprobe/README` under disposable roots.

### Matrix

| Phase and case | Environment/configuration | Result |
| --- | --- | --- |
| user / inherited | `HOME` points at controlled `.dpkg.cfg` | rc 0; user logger, pre-hook, and post-hook ran; configured path filter removed both controlled package paths; configured user log created |
| user / appended controls | inherited plus replacement status/pre/post hooks, final path include, target log | rc 141; original logger and pre-hook already ran; later command hooks did not erase configured hooks |
| user / scrubbed | `env -i`, no `HOME`, target `TMPDIR` and canonical PATH | rc 0; no user-configured command ran; `/opt` path present; system docker path filter still removed documentation path |
| user / scrubbed plus include | previous case plus final `--path-include=*` | rc 0; both controlled package paths present; target log created |
| system / scrubbed baseline | `env -i` plus controlled `/etc/dpkg/dpkg.cfg.d` fragment | rc 0; system logger, pre-hook, and post-hook ran; configured path filter removed controlled paths |
| system / appended command controls | previous case plus replacement command hooks | rc 141; original logger and pre-hook already ran; replacements did not erase configured commands |
| system / neutralize data only | controlled system commands plus final path include and target log | rc 0; system logger, pre-hook, and post-hook still ran; both package paths present; target log selected |

### Classification

- `rc=141` is an expected losing control. The extra status logger exits and closes its pipe while the original configured logger has already executed. It demonstrates that appending a replacement logger is not a safe reset mechanism.
- Clearing the environment closes the user-configuration path because `HOME` is absent.
- Clearing the environment does not close the system-configuration path.
- Final path include and target log options neutralized the tested data-only path-filter/log classes.
- Command-bearing `pre-invoke`, `post-invoke`, and `status-logger` remained active.
- The temporary system configuration fragment was absent at probe completion: `cleanup=system-config-absent`.

## Combined matrix

| Case | Baseline/component evidence | Candidate/component evidence | Exact run or test | Result identity |
| --- | --- | --- | --- | --- |
| Credential/session inheritance | values and fake socket reached script | names-only refusal and dpkg scrub | LF-02 / PR #57 workflow | `30530666222`; `30536237092` |
| Apt auth compatibility | ambient | preserved to apt only | PR #57 workflow | `30536237092` |
| Target TMPDIR | unset, host `/tmp` | exact `<target>/tmp`, 1777, cleanup | PR #74 workflow | `30537488127`; artifact `8757263774`; `sha256:a5ede53dda2f63081e1fe51c811761ff328b605ca6722d12a1e75ee264cbc390` |
| Inner PATH mutation | fake dpkg/helper wins | configured `DPkg::Path` wins | PR #368 dedicated workflow | `30650100748` |
| Outer env mutation | fake caller env wins | `/usr/bin/env` wins | PR #368 dedicated workflow | `30650100748` |
| Direct Essential transaction | mutation distinctions | success and expected package set | PR #368 direct transaction | `30650100748` |
| APT-managed transaction | mutation distinctions | success and expected package set | PR #368 APT transaction | `30650100748` |
| Direct/APT result comparison | n/a | equal installed package sets | PR #368 | artifact `8801028296`; `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |
| Fakeroot compatibility | discriminator | environment and target TMPDIR preserved | PR #57/#74 | `30536237092`; `30537488127` |
| Cleanup guard | unsafe overlap accepted by predecessor | exact runtime guard rejects repo/HOME overlap | PR #368 | `30650100748` |
| User dpkg config | inherited command hooks execute | scrub removes `HOME` and user config | retained dpkg probe | artifact receipt above |
| System dpkg config | configured command hooks execute | four-patch scrub does not address this owner | LF-02 and retained dpkg probe | separate HOLD |
| Immediate rerun | required | passed in component carriers | PR #57/#74/#368 | carrier runs above |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Patch application | ordered `git apply --check` against exact mirror/current upstream | NOT RUN | none |
| Perl syntax | `perl -c mmdebstrap` | NOT RUN on candidate | none |
| Formatting | project perltidy invocation with `.perltidyrc` | NOT RUN on candidate | none |
| `tests/chrootless` | upstream test runner for current suite | NOT RUN | none |
| `tests/chrootless-fakeroot` | upstream test runner for current suite | NOT RUN | none |
| Direct transaction fixture | landed LF transaction adapted to candidate | NOT RUN | none |
| APT transaction fixture | landed LF transaction adapted to candidate | NOT RUN | none |
| System dpkg-config controls | controlled hooks on direct/APT candidate paths | NOT RUN | none |
| Relevant complete package/coverage gate | select after current source review | NOT RUN | none |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| LF-02 privileged host integrations | run `30530666222` | success; exposure confirmed | `8754537765`; `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b` |
| Environment security | run `30536237092` | success | `8756781699`; `sha256:c9eb96221d6fe7144c2b3dfa050f322d56f1cce4ce2f9c6b7feab197b68f949a` |
| Target TMPDIR | run `30537488127` | success | `8757263774`; `sha256:a5ede53dda2f63081e1fe51c811761ff328b605ca6722d12a1e75ee264cbc390` |
| Complete repository CI for executable authority | run `30650101464` | success | PR #368 head |
| Dedicated executable-authority workflow | run `30650100748` | success | `8801028296`; `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |
| Dpkg config isolation | retained script and receipt | expected distinctions passed; cleanup verified | hashes above |

## Patch application and rebase

- released/imported base identity: `6fde999741f4fe1e7bf38079acf29432ef87a35e`;
- controlled mirror base: `574048f2a720057b75e56622003932f344dc700a`;
- imported source blob after local environment/TMPDIR components: `41aa46f989a2660cebdb0138e0847cde25b269a3`;
- patch application command: listed above;
- fuzz/offset result: PR #368 reports its two patches applied with zero fuzz to the imported source; complete four-patch application from released mirror source remains unexecuted;
- conflict resolution: none performed in this pass;
- complete diff reviewed: carrier source hunks and ordering reviewed; final mirror-candidate diff pending;
- active overlap searched: Linux Fieldwork carriers reviewed; current Salsa/BTS search pending.

## Cleanup and rerun

The dpkg probe used disposable roots and one unique system configuration fragment. Its trap removed the fragment on ordinary exit and handled HUP/INT/TERM; the ordinary path also removed it before the final assertion. The receipt ended with `cleanup=system-config-absent`. No process, socket, mount, package target, or system fragment remains from the probe.

Intentional retained state consists of packet commits, the probe/receipt, the Linux Fieldwork branch, the unchanged mirror candidate branch, and internal #397 coordination.

## Tests not run

- exact current Salsa master checkout and blob verification;
- complete ordered patch application to the mirror candidate;
- full-series direct and apt-managed transaction matrix;
- system dpkg-hook controls through actual mmdebstrap direct and apt-managed paths on the candidate;
- detector benign near-match/mixed-case controls on current source;
- residual `/proc` and host-file controls;
- non-chrootless source/runtime control;
- current `tests/chrootless` and `tests/chrootless-fakeroot`;
- current formatting, lint, syntax, and package gates;
- broader private-repository/authentication matrix;
- broader QEMU/fakeroot combinations;
- dpkg configuration classes beyond command hooks, path filters, and log destination.

## Failure classification

The failed current-master retrieval belongs to environment/tooling access: Salsa project metadata and released sources were readable, while branch API/raw master retrieval and direct DNS-backed clone/download were unavailable in this execution environment. No product failure is inferred from that limitation.

The two `rc=141` probe cases are successful losing controls, not unexplained failures. They prove that additive status-loggers are unsafe as a reset strategy.

## Final evidence statement

The reviewed carriers establish each source correction and the composed executable-authority pair on imported Debian `1.5.7-3`. The new probe establishes that the environment scrub removes user dpkg configuration but leaves system dpkg configuration active, including command-bearing hooks. The four-patch candidate remains coherent; system dpkg-config isolation is a separate held correction. Promotion of the four-patch unit still requires exact mirror/current-upstream application and one final-state transaction/native-test matrix.