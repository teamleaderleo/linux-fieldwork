# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | released/imported `6fde999741f4fe1e7bf38079acf29432ef87a35e`; current Salsa `master` unresolved |
| Candidate head | no current-upstream candidate yet |
| Linux Fieldwork head | see `HANDOFF.md` |
| Platform/distribution | inherited carrier runs: GitHub-hosted Debian/current sid environments |
| Architecture | inherited carriers primarily amd64 |
| Kernel | see retained workflow artifacts; unqueried in this pass |
| Shell/runtime | Bash, Perl, Python fixtures in linked carriers |
| Privilege boundary | unprivileged chrootless, fakeroot, and dedicated privileged LF-02 controls |
| Important tool versions | exact versions remain in carrier artifacts; current-upstream rerun pending |

## Evidence classification for this pass

No product transaction was executed during this pass. The work performed was carrier review, exact identity extraction, source-overlap analysis, and retention of an ordered four-patch product series. Every green/red runtime result below is inherited from an exact linked carrier and is labeled with its run/artifact identity.

## Baseline reproducer

### Command

Canonical commands live in PR #22, PR #57, PR #74, and PR #368 transaction scripts. The current-upstream baseline command remains to be created after resolving exact Salsa master.

### Expected distinguishing result

Released source without the series should expose the original chrootless boundary: ambient environment inheritance, caller executable authority, and no product-level target-TMPDIR helper.

### Observed result

- LF-02 status: workflow success while confirming exposure;
- run: `30530666222`, job `90831976076`;
- artifact: `8754537765`;
- digest: `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b`;
- changed state: fake credentials/session variables reached package script; fake agent socket received canary; host integrations were observed under dedicated controls;
- cleanup: carrier reports retained evidence only.

## Candidate reproducer

### Command

Pending exact current-upstream checkout. Required application sequence:

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

Current-upstream candidate: `NOT RUN`.

## Matrix

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
| Immediate rerun | required | passed in component carriers | PR #57/#74/#368 | carrier runs above |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Patch application | ordered `git apply --check` against exact Salsa master | NOT RUN | none |
| Perl syntax | `perl -c mmdebstrap` | NOT RUN on current upstream | none |
| Formatting | project perltidy invocation with `.perltidyrc` | NOT RUN on current upstream | none |
| `tests/chrootless` | upstream test runner for current suite | NOT RUN | none |
| `tests/chrootless-fakeroot` | upstream test runner for current suite | NOT RUN | none |
| Direct transaction fixture | landed LF transaction adapted to candidate | NOT RUN | none |
| APT transaction fixture | landed LF transaction adapted to candidate | NOT RUN | none |
| Relevant complete package/coverage gate | select after current source review | NOT RUN | none |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| LF-02 privileged host integrations | run `30530666222` | success; exposure confirmed | `8754537765`; `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b` |
| Environment security | run `30536237092` | success | `8756781699`; `sha256:c9eb96221d6fe7144c2b3dfa050f322d56f1cce4ce2f9c6b7feab197b68f949a` |
| Target TMPDIR | run `30537488127` | success | `8757263774`; `sha256:a5ede53dda2f63081e1fe51c811761ff328b605ca6722d12a1e75ee264cbc390` |
| Complete repository CI for executable authority | run `30650101464` | success | PR #368 head |
| Dedicated executable-authority workflow | run `30650100748` | success | `8801028296`; `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676` |

## Patch application and rebase

- released/imported base identity: `6fde999741f4fe1e7bf38079acf29432ef87a35e`;
- imported source blob after local environment/TMPDIR components: `41aa46f989a2660cebdb0138e0847cde25b269a3`;
- patch application command: listed above;
- fuzz/offset result: PR #368 reports its two patches applied with zero fuzz to the imported source; complete four-patch application from released source remains unexecuted;
- conflict resolution: none performed in this pass;
- complete diff reviewed: carrier source hunks and their ordering reviewed; current-upstream final diff pending;
- active overlap searched: Linux Fieldwork carriers reviewed; current Salsa/BTS search pending.

## Cleanup and rerun

This pass created only GitHub branch commits and issue comments. It started no local product process, socket, mount, container, package transaction, or temporary target. Intentional retained state is the packet branch, patch series, and #397 internal claim/checkpoint. Carrier cleanup statements remain linked evidence and were not re-executed.

## Tests not run

- exact current Salsa master checkout and blob verification;
- complete ordered patch application;
- full-series direct and apt-managed transaction matrix;
- detector benign near-match/mixed-case controls on current source;
- residual `/proc` and host-file controls;
- non-chrootless source/runtime control;
- current `tests/chrootless` and `tests/chrootless-fakeroot`;
- current formatting, lint, syntax, and package gates;
- broader private-repository/authentication matrix;
- broader QEMU/fakeroot combinations.

## Failure classification

The failed current-master retrieval belongs to environment/tooling access: Salsa project metadata and released sources were readable, while branch API/raw master retrieval and direct DNS-backed clone/download were unavailable in this execution environment. No product failure is inferred from that limitation.

## Final evidence statement

The reviewed carriers establish each source correction and the composed executable-authority pair on the imported Debian `1.5.7-3` source. This pass establishes a coherent four-patch order and preserves exact evidence identities. Promotion requires exact current-upstream application and a single final-state transaction/native-test matrix.