# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Current upstream repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Imported native test blob | `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Prior candidate head | `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Linux Fieldwork starting head | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Platform/distribution | Debian GNU/Linux 13 (trixie) 13.3 |
| Architecture | x86_64 |
| Kernel | `6.12.13` |
| Shell/runtime | Bash; Python 3.13.5 |
| Privilege boundary | unprivileged, in-memory archives only |
| Important tool versions | Python 3.13.5; GNU patch 2.8 available |

## Baseline reproducer

### Command

```sh
python3 upstream-packets/units/19-tarfilter-pax-idshift/scripts/test_pax_idshift.py
```

The script executes a losing baseline model and a repaired candidate model in one run. Its baseline path changes `TarInfo.uid`/`gid` while retaining the PAX numeric strings, matching the current source order.

### Expected distinguishing result

- large member starts at uid `1000000000`, gid `1000000001` with PAX numeric keys;
- after `+7`, baseline output still reads as `1000000000:1000000001`;
- ordinary member shifts from `1000:1001` to `1007:1008`.

### Observed result

- status: `0`; all assertions passed;
- output excerpt:

```json
{
  "baseline_large": [1000000000, 1000000001],
  "baseline_small": [1007, 1008]
}
```

- changed state: in-memory archives only;
- surviving resources: none;
- output receipt SHA-256: `6ce3c5c73506862bf60397f1efb476d269a58156c3fa798d86d2c27d059550b4`.

## Candidate reproducer

### Command

Same command; the candidate path removes PAX `uid`/`gid` immediately after shifting.

### Expected result

- large output reads as `1000000007:1000000008`;
- regenerated PAX values equal the shifted decimal strings;
- ordinary output reads as `1007:1008` without numeric PAX keys;
- unrelated PAX comments and payloads remain;
- `-7` returns both members to their original IDs.

### Observed result

- status: `0`; all assertions passed;
- output excerpt:

```json
{
  "candidate_large": [1000000007, 1000000008],
  "candidate_large_pax": ["1000000007", "1000000008"],
  "candidate_small": [1007, 1008],
  "unrelated_pax_preserved": ["keep-large", "keep-small"],
  "roundtrip": {
    "large": [1000000000, 1000000001],
    "small": [1000, 1001]
  }
}
```

- changed state: in-memory archives only;
- surviving resources: none;
- script SHA-256 in the execution environment: `0e465b654d9d3e27098a05229e41252fa804f75ec5bd36633f9478508d6852fe`.

## Matrix

| Case | Baseline | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Large PAX uid/gid +7 | reads original IDs | reads shifted IDs | packet script | `1000000000:1000000001` vs `1000000007:1000000008` |
| Ordinary uid/gid +7 | shifts | shifts | packet script | `1007:1008` both paths |
| Regenerated numeric PAX | retains old strings | emits shifted strings | packet script | `1000000007`, `1000000008` |
| Unrelated PAX metadata | retained | retained | packet script | `keep-large`, `keep-small` |
| Payloads | retained | retained | packet script | assertions pass |
| Inverse -7 | large path would begin from stale output | restores original candidate output IDs | packet script | large and small original IDs restored |
| Immediate rerun | deterministic | deterministic | two consecutive script executions plus `cmp` | outputs identical |
| Prior exact-source regression | loses on unmodified imported script | passes retained patch | `python3 -m unittest tests.test_tarfilter_pax_idshift -v` in PR #78 | CI run `30538012863` success |
| Draft native detector block | status 1 with exact diagnostic | status 0 | extracted addition from `patches/0002-tests-cover-pax-idshift.patch` against minimal source-faithful models | baseline stderr `large ownership was not shifted`; candidate stderr empty |

## Native test materialization pass

The imported `tests/tarfilter-idshift` file was inspected at blob `6956e76aca153147d3a8a6668196d913ebc8a49e`. It already owns:

- PAX xattr retention;
- zero-shift byte identity;
- ordinary `+100000` ownership shifting through extraction;
- inverse-shift byte identity.

The smallest native extension therefore stays in this file and adds only the missing large numeric-PAX discriminator plus an ordinary control. The draft is retained as `patches/0002-tests-cover-pax-idshift.patch`.

### Draft detector validation

The newly added shell/Python block was extracted and run against two minimal models that reproduce the exact current and selected id-shift ordering:

```text
baseline_status=1
candidate_status=0
baseline stderr: large ownership was not shifted
candidate stderr: empty
```

Receipt identities:

- complete native-test diff SHA-256: `1e0e984de35ca911ad2a015bc1046b1ecd861790b5bb39fe43b45a38a2f7b609`;
- retained `0002` patch SHA-256: `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`;
- extracted detector block SHA-256: `5b8baf56cfd1c5264654ea395494d362dc28167e85dd221d93dba2a443631043`;
- baseline model SHA-256: `988f7d6a93f253ff7a02eb270d666f0c6ed2cfe99e9d0ca5bdef8dd0748d7487`;
- candidate model SHA-256: `0a88fb2f61fe43efcb85d81888bbac825ba09d7c9a3b40917d357b922cd6419f`.

This validates the detector's losing and winning behavior. It does not substitute for applying both patches to the exact current upstream checkout and running the complete native test.

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Existing native id-shift test | project entry point for `tests/tarfilter-idshift` | NOT RUN; current upstream checkout unavailable in this execution environment | NEEDS BRANCH |
| Proposed large-ID native regression | apply `0002`, then run focused entry point | DRAFTED; detector block loses on current model and passes on candidate model; complete native file NOT RUN | NEEDS BRANCH |
| Formatting/lint | project-declared checks affecting `tarfilter` and test shell | NOT RUN | NEEDS BRANCH |
| Ordinary repository gate | project-declared relevant coverage invocation | NOT RUN | NEEDS BRANCH |

The repository README documents the broad suite as `./make_mirror.sh` followed by `CMD=./mmdebstrap ./coverage.sh`. This unit should first use the repository's focused mechanism for the named test and record whether broad mirror setup is proportionate or required by maintainers.

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| Exact imported-source regression | PR #78 / `tests.test_tarfilter_pax_idshift` | PASS | run `30538012863`, exact head `8d6443626e4338b180ec0533969bfe4d32b20d52` |
| Exact-head independent review | PR #78 review | ACCEPT | review recorded against exact head |
| Fresh semantic probe | `python3 /tmp/unit19_probe.py` | PASS | output SHA-256 `6ce3c5c73506862bf60397f1efb476d269a58156c3fa798d86d2c27d059550b4` |
| Immediate rerun | second execution and `cmp` | PASS | byte-identical output |
| Current source review | canonical repository and Debian source inspection | defect still present | tarfilter file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Native test-owner inspection | `upstream/mmdebstrap/tests/tarfilter-idshift` | COMPLETE | blob `6956e76aca153147d3a8a6668196d913ebc8a49e` |
| Native detector model run | extracted `0002` addition against baseline/candidate models | expected FAIL/PASS | statuses `1/0`; exact diagnostic above |

## Patch application and rebase

- current upstream base identity observed: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- current tarfilter file identity: unchanged from the source reviewed by issue #37 and PR #78;
- retained upstream-root source patch: `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`;
- source patch SHA-256: `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303`;
- retained native test patch: `patches/0002-tests-cover-pax-idshift.patch`;
- native test patch SHA-256: `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`;
- intended commands: `git apply --check` for both patches, followed by `git apply` in source-then-test order;
- fuzz/offset result on full current checkout: NOT RUN;
- conflict resolution: none performed;
- complete diff reviewed: source hunk and draft native-test hunk reviewed independently; exact applied two-file diff pending;
- active overlap searched: 2026-08-01, no indexed equivalent found.

## Cleanup and rerun

The fresh packet probe used only `/tmp/unit19_probe.py`, `/tmp/unit19_probe.out`, and `/tmp/unit19_probe_rerun.out`, with in-memory tar archives. It started no child services, sockets, mounts, containers, or package operations. The command passed twice consecutively and produced byte-identical JSON output.

The native test drafting pass used disposable copies of the imported test, one generated unified diff, two minimal model scripts, and temporary PAX archives under `/tmp`. The test block's own trap removes generated archives. No service, socket, mount, container, lock, package operation, or caller-controlled path was involved.

The Linux Fieldwork branch intentionally retains packet documents, both patches, and the packet script. No imported source or imported test file was modified.

## Tests not run

- exact current upstream checkout patch application;
- complete native `tests/tarfilter-idshift` baseline and candidate runs;
- project formatting/lint;
- broad coverage suite and mirror preparation;
- alternate Python releases;
- GNU tar, bsdtar/libarchive, and other reader interoperability beyond existing native extraction coverage;
- package build and Debian autopkgtest.

The execution environment lacked network DNS access for cloning, and no controlled upstream fork was verified. Existing exact-source CI and the new losing/winning detector support the source correction; they do not replace current-head native execution.

## Failure classification

- PR #78 early revisions: patch packaging failure; malformed or under-contextualized retained diffs prevented semantic execution.
- PR #78 final revision: packaging repaired through block replacement; semantic assertions executed and passed.
- Fresh baseline: product metadata-authority failure; stale PAX strings override shifted fields.
- Native detector baseline model: intended product failure with exact diagnostic `large ownership was not shifted`.
- Current clone attempt: environment/tooling failure; DNS resolution unavailable, with zero source mutation.

## Final evidence statement

The executed matrix establishes that stale PAX numeric ownership overrides changed `TarInfo` fields, that removing only `uid` and `gid` lets Python serialize the requested shifted identity, that ordinary numeric headers remain ordinary, that unrelated PAX metadata and payloads survive, and that inverse shifting restores the original IDs. The current public source still contains the losing block. The existing native test owner is now exact, and a detector extension has demonstrated independent losing and winning outcomes. Readiness still requires clean application to the current upstream checkout and complete native exact-head gates.
