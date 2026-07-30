# LF-02 chrootless upgrade failure and recovery

## In simple words

The clean LF-02 install probe does not show what happens during a real package upgrade or after a maintainer script fails. This investigation separates unpack from configure, preserves a deliberately edited conffile, forces one `postinst` failure, then attempts a later recovery and purge.

Tracking: issue #174.

## Question

Under direct chrootless `dpkg --root` execution:

1. does version 1 → version 2 remain contained when unpack and configure are separate;
2. does explicit `--force-confold` preserve a locally edited conffile;
3. what target state remains after a version 3 `postinst` failure;
4. can version 3.1 recover that state;
5. what remains after purge;
6. which outside-target effects occur in each phase.

## Source

- Parent scout: issue #11 / PR #21
- Imported mmdebstrap revision: `debian/1.5.7-3`, resolved commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Investigation branch: `investigation/lf-02-upgrade-failure-recovery`
- Supported runner: `run-guarded.sh`
- Matrix implementation: `run.sh`
- Fixture builder: `build-fixtures.py`
- Summary builder: `summarize.py`
- Workflow: `.github/workflows/lf-02-upgrade-failure-recovery.yml`

Run the matrix through:

```sh
bash investigations/lf-02-upgrade-failure-recovery/run-guarded.sh
```

`run.sh` is the child implementation and remains behind the guarded entry point.

The first matrix uses the direct host `dpkg` boundary already mapped by the scout:

```text
--force-not-root
--force-script-chrootless
--force-confold
--root=<target>
--log=<target>/var/log/dpkg.log
```

Apt-managed upgrades, triggers, and dependencies are later boundaries.

## Environment

The dedicated workflow runs on GitHub-hosted Ubuntu 24.04 and records exact repository provenance, tool versions, UID/GID, kernel, package archive digests, commands, timing, target snapshots, host fingerprints, and per-process syscall traces.

Uploaded public evidence removes the account-name line from `environment.txt` and verifies its absence before artifact upload. UID and GID remain available for privilege interpretation.

The guarded entry point:

- rejects repository, home, relative, missing, and symlinked temporary roots;
- accepts canonical disposable roots below `/tmp` or `/var/tmp`;
- creates one unpredictable sandbox with `mktemp -d`;
- validates the fixed result path and rejects symlinked path components;
- removes only the exact validated sandbox with `rm -rf --`;
- starts the matrix in a new process group;
- forwards INT/TERM to that group, reaps the group leader, escalates after a bounded grace period, and exits 130/143;
- prevents later matrix phases after cancellation.

## Baseline

PR #21 retained clean direct install, reinstall, purge, install-after-purge, and two fresh mmdebstrap builds. It did not exercise:

- a version transition;
- separate unpack/configure;
- a changed conffile with a local edit;
- failed configuration state;
- recovery from failed configuration.

## Hypothesis

The expected retained behavior is:

- version 2 unpack leaves target status `unpacked`;
- version 2 configure reaches `installed`;
- the edited conffile remains unchanged under `--force-confold`;
- version 3 configure exits nonzero and leaves target status `half-configured`;
- version 3.1 unpack/configure recovers to `installed`;
- purge removes the tracked payload and principal conffile;
- maintainer-script-created logs may remain below the target as ordinary untracked package data;
- no successful unexpected mutation occurs outside the target.

Host dpkg configuration may still invoke the already-known needrestart status logger. That is classified as a service action rather than confused with target package state.

## Reproduction matrix

1. build `lf-lifecycle` 1.0, 2.0, 3.0-failing, and 3.1-recovery archives;
2. initialize an empty target dpkg database;
3. install 1.0;
4. replace `/etc/lf-lifecycle.conf` below the target with `user=preserved`;
5. unpack 2.0;
6. configure 2.0;
7. unpack 3.0;
8. configure 3.0 and require a nonzero result;
9. unpack 3.1;
10. configure 3.1;
11. purge the package;
12. classify all outside-target path and Unix-socket events;
13. compare host fingerprints.

Each phase retains its raw and normalized command, stdout, stderr, status, timing, traces, target status, tree manifest, payload, conffile siblings, and maintainer-script log.

## Distinguishing results

- **Product candidate:** successful unexpected host mutation, host package state used as target state, a host service action, a successful exit for the deliberately failing configure, failure to recover, or conffile behavior contradicting `--force-confold`.
- **Mapped behavior:** expected target-local partial state, later recovery, target-local residue, and only fully classified host reads/runtime effects.
- **Blocked:** unresolved outside access or an environment that cannot distinguish package failure from containment failure.

Promotion takes precedence over unresolved classification when both appear. A clean mapped result requires zero unexpected mutations, zero service actions, zero unresolved events, an unchanged host fingerprint, and a satisfied lifecycle contract.

## Evidence boundary

- The fixture is synthetic and cooperative except for the deliberate `postinst` failure.
- `--force-confold` is an explicit policy choice; this matrix does not characterize interactive conffile prompting.
- The syscall classifier observes path-bearing file/process/network calls. FD-only effects still require raw trace review.
- The first matrix does not yet prove apt-managed upgrade, dependency ordering, triggers, multiarch, or rollback semantics for arbitrary packages.
- A failed configure is expected evidence when the target status and later recovery match the declared contract.
- Direct invocation of `run.sh` bypasses the outer runtime and cancellation controls and is outside the supported execution contract.

## Validation contract

The summarizer uses explicit validation errors and exits status 2 for invalid evidence under both normal Python and `python -O`. Synthetic regressions mutate phase status, snapshot state, classifier totals, maintainer-script root/cwd, and conffile siblings; every mutation must fail identically in both modes.

Conffile paths and contents are exact per phase, including `.dpkg-new` during unpack, `.dpkg-dist` after configuration, transition from 2.0 to 3.0 to 3.1 contents, and an empty set after purge. Classifier totals are recomputed from category counts instead of trusting the retained boolean flag.

Disposition precedence is covered for clean, service-action, unexpected-mutation, unresolved-only, mixed service/unresolved, and host-fingerprint-change cases.

Guarded-runner regressions use real process groups and prove:

- repository paths are rejected as recursive-cleanup roots before the child command runs;
- natural child status 7 remains status 7 and the exact sandbox is removed;
- SIGINT stops the child group, removes the sandbox, prevents the later marker, and returns 130;
- SIGTERM does the same and returns 143.

## Results

Dedicated workflow run `30557757766` completed successfully at head `40c2b1ec89e4d8391bbcbe95a14f96a4a87760ca`. Review found safety and decision-contract gaps, so that run remains exploratory evidence.

Generic Linux Fieldwork CI run `30557757125` passed compilation and all nine inherited tests, then failed because the stacked base carried an older repository workflow that unconditionally invoked `scripts/capture-linux-context.sh`, which is absent from that base. This is a base-composition failure outside the investigation diff.

Helper B added public-evidence account-name removal at commit `353e963f1200eae7733e8f0814f2e18ccf53270b`. Run `30577790248` validated the scrub and exposed the prior decision defect by reporting 32 service actions with `retain-mapped-behavior`.

Helper B then replaced assertion-only summary validation, added exact conffile sibling/content checks, recomputed classifier totals, and defined disposition precedence. Dedicated workflow run `30578410231` at exact head `6f9f89c432982f1227a1fd3b45ab9236c8ade96c` passed the revised decision contract and reported:

```text
disposition=promote-product-candidate
failure_recovery: exit=1 failed_status=half-configured recovery_status=installed payload=3.1
containment: unexpected_mutations=0 service_actions=32 unresolved=0 host_fingerprint_unchanged=true
```

Helper B added the guarded process-group entry point and real-process cleanup/cancellation regressions. Dedicated workflow run `30579252048` at code head `1f8badfb91d75dbff21e6bf83cc0e439a1630c86` passed:

- Python and shell syntax;
- all LF-02 summary, provenance, schema, unsafe-root, child-status, SIGINT, and SIGTERM regressions;
- the full matrix through `run-guarded.sh`;
- account-name removal;
- artifact upload and downloaded-artifact receipt.

The package lifecycle recovered as expected. The 32 classified host service actions trigger the declared promotion result.

## Next step

Refresh or restack the branch onto a current base so generic repository CI can act as a merge signal. Confirm the policy choice for classified service actions: issue #174 permits mapped treatment, while this branch follows the stricter promotion rule requested during review. Keep the PR in draft until those two human decisions are resolved.

## Authority

Internal Linux Fieldwork investigation only. No upstream contact.
