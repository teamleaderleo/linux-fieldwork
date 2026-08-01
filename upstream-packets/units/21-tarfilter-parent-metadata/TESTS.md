# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Upstream base | `josch/mmdebstrap main@77ec9be5417ee44c96343d2347145585da1b1f94` (identity review only) |
| Candidate head | `NEEDS FORK`; retained patch SHA-256 `16d0c6c5e6e26a513fdc7b84ef0bd99a94f60f5e2f30dec83d777169223c67d1` |
| Linux Fieldwork head | see `HANDOFF.md` |
| Platform/distribution | Debian GNU/Linux 13.3 (trixie) |
| Architecture | x86_64 |
| Kernel | Linux 6.12.13 |
| Shell/runtime | `/bin/sh`; Python 3.13.5 |
| Privilege boundary | unprivileged local files; extraction used `tar --no-same-owner` |
| Important tool versions | GNU tar 1.35; git 2.47.3 |

## Baseline reproducer

### Command

```sh
python3 upstream-packets/units/21-tarfilter-parent-metadata/scripts/reproduce-parent-metadata.py \
  > /tmp/unit21-local-matrix.json
```

The retained script models the exact current path-filter tuple, translated-regex prefix extraction, last-match-wins loop, and streaming `TarInfo` pass-through relevant to this defect.

### Expected distinguishing result

With `--path-exclude='/*' --path-include='/usr/bin/tool'`, baseline output contains only `usr/bin/tool`; GNU tar creates missing parents with default mode `0755`.

### Observed result

- status: `0` for the matrix command; assertions passed;
- output archive members: `usr/bin/tool` only;
- extracted modes: `usr=0755`, `usr/bin=0755`, `usr/bin/tool=0755`;
- lost state: explicit parent uid, gid, mtime, modes, and PAX markers;
- receipt: `artifacts/local-matrix.json`, SHA-256 `5f80370c5ce6ec88a2b4fe1c5c111665c1cba6b991f2f8666a394bd8e048e004`.

## Candidate reproducer

### Command

```sh
python3 upstream-packets/units/21-tarfilter-parent-metadata/scripts/reproduce-parent-metadata.py \
  > /tmp/unit21-local-matrix.json
```

### Expected result

Candidate output contains `usr`, `usr/bin`, and `usr/bin/tool`; archive and extraction preserve parent modes and archive metadata.

### Observed result

- status: `0`;
- output members: `usr`, `usr/bin`, `usr/bin/tool`;
- archive metadata: `usr` mode/uid/gid/mtime `0700/11/21/1700000001`, `usr/bin` `0711/12/22/1700000002`;
- PAX markers: `usr-parent` and `bin-parent` survived;
- GNU tar extracted modes: `0700`, `0711`, `0755`;
- receipt: same JSON artifact.

## Matrix

| Case | Baseline | Candidate | Exact command or test | Result identity |
| --- | --- | --- | --- | --- |
| Exact nested include | parents omitted | parents retained | local script; upstream test `exact` | distinguishing |
| Fixed-prefix wildcard `/usr/bin/*` | prefix derived from regex wrapper | ancestors retained | local relation matrix | pass |
| Mid-path wildcard `/usr/*/tool` | parents omitted | `/usr` and `/usr/bin` retained conservatively | local matrix; upstream test `wildcard` | pass |
| Character class `/usr/[bs]in/tool` | parents omitted | matching chain retained conservatively | local matrix; upstream test `character_class` | pass |
| Component boundary `/usr2/tool` | translated prefix unusable | `/usr` stays excluded; `/usr2` retained | local matrix; upstream test `component_boundary` | pass |
| Unrelated `/opt` | excluded | excluded | local relation matrix | pass |
| Leading wildcard `*/tool` | translated prefix unusable | all candidate parents retained conservatively | local relation matrix | pass |
| Ordinary leaf matching | last match wins | unchanged | source review | neutral control |
| Cleanup | temporary directories removed | same | script `finally` and shell traps | pass |
| Immediate rerun | pass | pass | repeated local execution | pass |

## Upstream-native gates

| Gate | Exact command | Result | Candidate head |
| --- | --- | --- | --- |
| Focused unit test | `CMD=./mmdebstrap ./coverage.py tarfilter-parent-metadata` | NOT RUN; no canonical checkout/candidate branch | NEEDS FORK |
| Direct focused script | `tests/tarfilter-parent-metadata` from upstream root | NOT RUN on full upstream candidate | retained patch only |
| Formatting/lint | repository formatting and line-length gates | NOT RUN on full candidate | retained patch only |
| Full coverage suite | `CMD=./mmdebstrap ./coverage.sh` with required mirror state | NOT RUN | retained patch only |
| Build/package test | Debian package/autopkgtest path | NOT RUN | retained patch only |

## Linux Fieldwork retained gates

| Gate or fixture | Exact command/run | Result | Artifact/digest |
| --- | --- | --- | --- |
| matrix script syntax | `python3 -m py_compile scripts/reproduce-parent-metadata.py` | PASS | script SHA-256 `e79cf6143083cf6d44dd0095c503209be73e52d0be17bc9332275956863ca951` |
| baseline/candidate matrix | `python3 scripts/reproduce-parent-metadata.py` | PASS | JSON SHA-256 `5f80370...48e004` |
| retained patch syntax/application | `git apply --check` then `git apply` on exact-context synthetic fixture | PASS | patch SHA-256 `16d0c6...c67d1` |
| patched Python hunk | `python3 -m py_compile tarfilter` in synthetic fixture | PASS | local run 2026-08-01 UTC |
| proposed shell test parse | `sh -n tests/tarfilter-parent-metadata` | PASS | test blob embedded in patch |
| proposed focused test | run against focused candidate executable implementing patch logic | PASS, four cases | local run 2026-08-01 UTC |
| rerun | repeat matrix and focused test after cleanup | PASS | no retained temp resources |

## Patch application and rebase

- base identity: intended canonical `77ec9be5417ee44c96343d2347145585da1b1f94`;
- patch application command: `git apply --index patches/0001-tarfilter-retain-parent-metadata.patch`;
- fuzz/offset result: exact-context synthetic fixture applied with no error; canonical checkout unexecuted;
- conflict resolution: none in synthetic fixture;
- complete diff reviewed: yes for retained patch;
- active overlap searched: 2026-07-31; none surfaced.

## Cleanup and rerun

The matrix deletes owned temporary directories. The proposed upstream test traps `EXIT`, `INT`, `TERM`, and `HUP` and removes its private `mktemp` directory. Synthetic repositories remain outside the packet only during local work and carry no processes, sockets, mounts, or locks. The matrix and focused test passed again after cleanup.

## Tests not run

- exact canonical patch application, because the environment lacked a materialized upstream checkout;
- current `coverage.py` focused invocation on full source;
- full `coverage.sh` suite and mirror preparation;
- Debian package build and autopkgtest;
- privileged ownership/xattr extraction checks;
- cross-version Python and non-GNU tar tests.

## Failure classification

The red baseline is a product-source failure: the parent-retention branch consumes translated regex text and compares ancestry in one direction. The unavailable canonical checkout is an environment/tooling limit. No red candidate run remains in the retained local matrix.

## Final evidence statement

Executed evidence proves the current source path drops explicit parents for an exact nested include and that the selected original-glob, component-bounded two-direction predicate retains their archive metadata across the focused matrix. It does not yet prove full upstream integration or project acceptance.
