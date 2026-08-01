# Adjacent repository pass — 2026-08-01

## Scope and stop rule

The project instructions require search-before-new-work and a bounded pass across only enough adjacent contexts to change the destination or test decision. This pass checked one maintained downstream family and the canonical project's current test surface, then stopped when the Debian package lane remained the only proven maintained affected destination and a regression-test gap became the actionable parallel lane.

No external issue, pull request, review, email, or maintainer contact was made.

## Context 1 — NixOS/nixpkgs

Exact package files checked:

| Branch | `package.nix` blob | util-linux version | Disposition |
| --- | --- | --- | --- |
| `nixos-25.11` | `2b49ddc54ff20cb9248a73112f68019e1654acb7` | `2.41.4` | no package backport target; newer than upstream fixed release `v2.41.2` |
| `nixos-26.05` | `f11d004bb0cf7db74e8e7de4e6410c57efbc8739` | `2.42.2` | fixed upstream release |
| current default branch | inspected during this pass | `2.42.2` | fixed upstream release |

Discriminator: upstream issue #4401 records the correction in `v2.41.2` and maintained stable branches. Therefore the maintained NixOS branches sampled here cannot add a missing destination for this unit.

## Context 2 — canonical util-linux test surface

Exact current source head: `fd82c4043fab942b889f478800118c66edfbc39f`.

Exact files inspected:

- fixed owner: `lib/path.c`, blob `90aac2058034143a7ccea5bf6f43f2831df492f0`;
- native lscpu harness: `tests/ts/lscpu/lscpu`, blob `1c25405a6f8e4bbe15c6bc92d879eaffc5a50b8c`;
- test framework: `tests/functions.sh`, blob `a54064b79f31cefbee59268578147518f03d8b1f`;
- util-linux build workflow: `.github/workflows/cibuild.yml`, blob `9c40d967ff9136e17de6d48ab54f91805d4202ec`.

Observations:

1. `ul_path_cpuparse()` has the canonical free-then-NULL error path.
2. The native lscpu harness iterates archived sysroot dumps and exercises text and parse modes.
3. Repository code search for the public malformed token `5,12-%` returned no indexed occurrence.
4. Repository code search for a test invocation of `ul_path_cpuparse()` returned only the implementation.

These searches are overlap controls, not a proof that no semantically equivalent test exists. The exact current harness nevertheless contains no generated malformed-cpuset subtest.

## Context 3 — controlled util-linux fork

Existing execution carrier discovered and retained:

```text
repository: teamleaderleo/util-linux
base branch: linux-fieldwork/unit-23-lscpu-cpuset-native-base
base head: 7669d148543822d56ffffa31d2f399f078f8e117
gate branch: linux-fieldwork/unit-23-lscpu-cpuset-native-gate
gate head: 95ebc67e521195741040ffebb58756b259fb69b2
internal draft PR: #1
focused run: 30691835019 — queued when checked
repository build run: 30691835043 — queued when checked
```

A separate current-master, test-only branch was created to preserve the regression-test candidate without changing the already queued stable-source gate:

```text
branch: linux-fieldwork/unit-23-cpuset-error-regression
base: fd82c4043fab942b889f478800118c66edfbc39f
head: cf8aadf90786200c8cb7006fa78db428d0229985
commit: tests: exercise malformed lscpu cpuset cleanup
changed file: tests/ts/lscpu/lscpu
product files changed: none
```

The candidate adds two native subtests, text and JSON, over the retained bounded 16-CPU sysroot with malformed `online` content `5,12-%`. Each requires `lscpu` to complete successfully after the parser rejects the malformed list. It reuses the exact fixture dimensions that distinguish Debian trixie `2.41-5` from the fixed candidate.

## Validation state and limitations

Completed:

- exact current-master base and one-file diff retained;
- shell control flow reviewed against `ts_init_subtest`, `ts_failed`, and `ts_finalize_subtest` semantics;
- fixture mutation and text/JSON modes match the proven Debian reproducer;
- no product implementation change;
- no public upstream proposal.

Not completed:

- the current-master test branch has not executed in hosted CI;
- the branch has not been run against an affected source revision with the test patch transplanted;
- `/proc/cpuinfo` is copied from the test host, so cross-architecture hermeticity still needs evidence;
- allocator-dependent end-to-end behavior means this candidate is not yet sufficient by itself for an upstream send decision;
- no sanitizer or architecture matrix has completed.

## Decision

Do not open another downstream package lane from this pass. Keep Debian trixie as the only proven maintained affected destination. Preserve the current-master regression-test branch as the next parallel technical action while the exact package and stable-source native runs remain queued.
