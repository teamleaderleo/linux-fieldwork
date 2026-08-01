# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Current upstream repository head observed | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current tarfilter file commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported tarfilter blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
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

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Existing native id-shift test | project entry point for `tests/tarfilter-idshift` | NOT RUN; current upstream checkout unavailable in this execution environment | NEEDS BRANCH |
| Proposed large-ID native regression | extend `tests/tarfilter-idshift`, then run focused entry point | NOT MATERIALIZED | NEEDS BRANCH |
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

## Patch application and rebase

- current upstream base identity observed: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- current tarfilter file identity: unchanged from the source reviewed by issue #37 and PR #78;
- retained upstream-root patch: `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`;
- intended command: `git am .../0001-tarfilter-regenerate-shifted-pax-ownership.patch`;
- fuzz/offset result on full current checkout: NOT RUN;
- conflict resolution: none performed;
- complete diff reviewed: source-only retained hunk reviewed; final source-plus-native-test diff pending;
- active overlap searched: 2026-08-01, no indexed equivalent found.

## Cleanup and rerun

The fresh probe used only `/tmp/unit19_probe.py`, `/tmp/unit19_probe.out`, and `/tmp/unit19_probe_rerun.out`, with in-memory tar archives. It started no child services, sockets, mounts, containers, or package operations. The command passed twice consecutively and produced byte-identical JSON output. Temporary local files were disposable execution evidence; the durable script is committed in this packet.

The Linux Fieldwork repository branch intentionally retains packet documents, patch, and script. No imported source file was modified.

## Tests not run

- exact current upstream checkout patch application;
- native `tests/tarfilter-idshift` baseline and candidate runs;
- project formatting/lint;
- broad coverage suite and mirror preparation;
- alternate Python releases;
- GNU tar, bsdtar/libarchive, and other reader interoperability;
- package build and Debian autopkgtest.

The execution environment lacked network DNS access for cloning, and no controlled upstream fork was verified. Existing exact-source CI supports the source correction; it does not replace current-head native execution.

## Failure classification

- PR #78 early revisions: patch packaging failure; malformed or under-contextualized retained diffs prevented semantic execution.
- PR #78 final revision: packaging repaired through block replacement; semantic assertions executed and passed.
- Fresh baseline: product metadata-authority failure; stale PAX strings override shifted fields.
- Current clone attempt: environment/tooling failure; DNS resolution unavailable, with zero source mutation.

## Final evidence statement

The executed matrix establishes that stale PAX numeric ownership overrides changed `TarInfo` fields, that removing only `uid` and `gid` lets Python serialize the requested shifted identity, that ordinary numeric headers remain ordinary, that unrelated PAX metadata and payloads survive, and that inverse shifting restores the original IDs. The current public source still contains the losing block. Readiness requires a clean current-upstream branch, native test integration, and exact-head upstream gates.
