# Source map

## Upstream source identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Primary implementation | `tarfilter` | upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94`; Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` | `PathFilterAction`; `path_filter_should_skip()` |
| Reference semantics | `guillemj/dpkg:src/main/filters.c` | `main` file blob `4fc1600a5717726faddc2fb556730f217e7f22a2` | raw pattern, fixed prefix, one-direction `strncmp()`, conservative comment |
| Upstream tests | `tests/tarfilter-idshift`, `coverage.txt` | GitHub mirror blobs `6956e76aca153147d3a8a6668196d913ebc8a49e`, `be105dd37f44c54b51a6f02ff4358f18c2ce618c` | test style and registration precedent |
| Build or package metadata | `coverage.py`, `coverage.sh`, `debian/rules` | current upstream page reviewed 2026-08-01 | full gates remain unexecuted |
| Contribution instructions | upstream README and Forgejo repository UI | repository page head `77ec9be541...` | pull-request destination; fork required |

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Canonical, component, evidence, superseded, or hold |
| --- | --- | --- | --- |
| Issue #397 | workflow merge `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` | priority and packet protocol | canonical routing |
| Issue #39 | open; created 2026-07-30 | defect report and original reproducer | canonical technical carrier |
| `upstream/unit-21-tarfilter-parent-metadata` | see `HANDOFF.md` and #397 checkpoint | retained patch, scripts, evidence, drafts | canonical unit branch |

## Candidate code

| File | Lines or symbols | Change | Owning commit or patch |
| --- | --- | --- | --- |
| `tarfilter` | `PathFilterAction.__call__` | retain original path glob beside compiled regex | retained patch 0001 |
| `tarfilter` | `path_filter_should_skip()` | derive literal prefix from original glob and compare both ancestry directions with component boundaries | retained patch 0001 |
| `coverage.txt` | tarfilter test registrations | register focused parent metadata test | retained patch 0001 |

## Candidate tests and evidence

| File | Test or fixture | Baseline/reference result | Candidate expectation |
| --- | --- | --- | --- |
| `tests/tarfilter-parent-metadata` | exact `/usr/bin/tool` include | exact current source omits `usr` and `usr/bin` | parents and metadata retained |
| same | wildcard `/usr/*/tool` | translated-regex prefix unusable | `usr` and `usr/bin` retained |
| same | class `/usr/[bs]in/tool` | translated-regex prefix unusable | matching ancestor chain retained conservatively |
| same | `/usr2/tool` boundary | naive raw prefix can alias names | only `usr2` chain retained |
| same | `/linkroot/tool` symlink parent | symlink omitted | symlink target and metadata retained |
| `scripts/reproduce-parent-metadata.py` | archive membership and extraction matrix | baseline parent modes become `0755` | explicit `0700`/`0711` survive |
| `scripts/compare-dpkg-parent-retention.py` | dpkg fixed-prefix model versus candidate | exact ancestors false; sibling aliases true | exact ancestors true; sibling aliases false; wildcard conservatism preserved |
| `artifacts/exact-source-validation.txt` | exact source application receipt | exact blob loses | patched exact source passes |
| `artifacts/dpkg-comparison.json` | eight compatibility assertions | mixed dpkg outcomes | explicit selected outcomes |

## Patch and branch links

- Linux Fieldwork branch: `upstream/unit-21-tarfilter-parent-metadata`
- Controlled upstream fork: `NEEDS FORK`
- Candidate upstream branch: `NEEDS BRANCH`
- Compare or diff: `NEEDS FORK`
- Retained patch or series: `patches/0001-tarfilter-retain-parent-metadata.patch`
- Patch application command:

```sh
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check /path/to/0001-tarfilter-retain-parent-metadata.patch
git apply --index /path/to/0001-tarfilter-retain-parent-metadata.patch
```

## Operation ownership map

| Operation | Owner before candidate | Owner after candidate | Evidence |
| --- | --- | --- | --- |
| compile path glob | `PathFilterAction` | same | upstream source |
| retain original glob | absent | `PathFilterAction` tuple | patch hunk 1 |
| decide ordinary include/exclude | compiled `fnmatch.translate()` regex, last match wins | same | patch preserves match loop |
| decide excluded parent retention | translated regex text plus one-direction `startswith()` | original glob literal prefix plus bounded two-direction relation | patch hunk 2; exact-source test |
| preserve tar metadata | streaming `TarInfo` pass-through when member survives | same | candidate manifest receipt |
| create missing parents during extraction | extraction tool | avoided when explicit parents survive | GNU tar extraction receipt |
| define compatibility precedent | dpkg raw pattern and plain fixed-prefix `strncmp()` | dpkg wildcard intent plus exact ancestry and component separators | comparison script/artifact |

## Overlap and current upstream state

Search date: 2026-08-01. Canonical mmdebstrap source still carried the affected logic and no active equivalent parent-metadata issue or pull request surfaced. Current dpkg source was reviewed through the maintainer's GitHub mirror at file blob `4fc1600…`. Recheck mmdebstrap overlap immediately before any authorized submission.

## Files deliberately not changed

- `PaxFilterAction` and PAX include/exclude semantics;
- type filtering and unit 22 regular-file aliases;
- transform, strip-components, idshift, and output serialization;
- path normalization handled by unit 20;
- hard-link dependency handling owned by unit 16;
- dpkg source itself, used only as a compatibility reference.
