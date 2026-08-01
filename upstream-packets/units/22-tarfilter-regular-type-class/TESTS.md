# Tests and evidence

## Exact retained identities

- Canonical upstream: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Exact current upstream base: `main@77ec9be5417ee44c96343d2347145585da1b1f94`
- Current relevant `tarfilter` content: Linux Fieldwork Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Current source still contains the defective `REGTYPE`/`0` mapping to `tarfile.REGTYPE` only
- Debian package revision: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Retained candidate head: `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`
- Candidate merge commit: `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Historical Linux Fieldwork CI: run `30537313944`, success
- Historical focused test: `tests/test_tarfilter_legacy_regular_type.py` at the retained candidate head
- Current internal integration PR: Linux Fieldwork draft PR #410
- Current hosted exact-source run: queued; record the final exact-head run in this file and `HANDOFF.md` when GitHub starts and completes it

## Historical exact-source command

```sh
python3 -m unittest tests.test_tarfilter_legacy_regular_type -v
```

The test applies the retained patch to an exact temporary copy of imported source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

## Historical baseline/candidate matrix

| Case | Expected baseline | Retained exact-head result |
| --- | --- | --- |
| Fixture parses `REGTYPE`, `AREGTYPE`, `DIRTYPE` distinctly | yes | pass |
| Baseline `--type-exclude=REGTYPE` removes `zero-regular` | yes | pass |
| Baseline `--type-exclude=REGTYPE` leaks `nul-regular` | distinguishing negative control | pass |
| Baseline retains directory | yes | pass |
| Candidate `--type-exclude=REGTYPE` retains only directory | yes | pass |
| Candidate `--type-exclude=0` retains only directory | yes | pass |
| Candidate `--type-exclude=DIRTYPE` retains both regular encodings | yes | pass |
| Exact-head Linux Fieldwork CI | success | run `30537313944`, success |
| Exact-head review | accepted | PR #77 review `4818250508` |

## Current-upstream verification

Current upstream project inspection established:

- repository: `josch/mmdebstrap`;
- branch/head: `main@77ec9be5417ee44c96343d2347145585da1b1f94`;
- relevant `tarfilter` content matches blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
- current selector mapping remains:

```python
case "REGTYPE" | "0":
    items.append(tarfile.REGTYPE)
```

The upstream README documents the complete suite through `coverage.sh` and individual named tests through:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable <test-name>
```

`coverage.py` enforces a one-to-one match between files under `tests/` and `Test:` entries in `coverage.txt`, copies `./tarfilter` to `shared/tarfilter`, materializes the selected test as `shared/test.sh`, runs shellcheck and shfmt, and dispatches through `run_null.sh`, `run_qemu.sh`, or the sudo path. `run_null.sh` invokes the generated file with `sh -x`.

## Proposed upstream-native assets

- Shell test: `native/tests/tarfilter-regular-type-class`
- Registry stanza: `native/coverage.txt.fragment`
- Linux Fieldwork gate: `tests/test_unit22_tarfilter_native_packet.py`

The Linux Fieldwork gate requires:

1. exact source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
2. exact registry stanza `Test: tarfilter-regular-type-class`;
3. baseline native-test failure with `nul-regular` present in the diagnostic;
4. GNU patch application with `--fuzz=0`;
5. candidate native-test success twice.

## Local native-test characterization

Environment:

```text
Python 3.13.5
Linux 6.12.13 x86_64
GNU tar 1.35
GNU patch 2.8
shellcheck: unavailable
shfmt: unavailable
```

A local semantics probe established:

```text
tarfile.REGTYPE  == b"0"
tarfile.AREGTYPE == b"\0"
TarInfo(type=REGTYPE).isfile()  == True
TarInfo(type=AREGTYPE).isfile() == True
```

Python USTAR writing and reading preserved both type bytes and payloads distinctly. GNU tar 1.35 listed and extracted both as ordinary regular files with exact payloads `zero\n` and `nul\n`.

The retained native shell test was then run against a minimal faithful model of the relevant tarfilter selection/copy loop:

```text
baseline return code: 1
baseline diagnostic: unexpected members for REGTYPE: {'nul-regular': (b'\x00', b'nul\n'), 'directory': (b'5', None)}
candidate run 1: success
candidate run 2: success
```

This characterizes the native test itself and its cleanup/rerun behavior. It does not replace the hosted exact-source gate or a complete upstream checkout.

## Patch review

Retained source diff:

```diff
-                items.append(tarfile.REGTYPE)
+                items.extend((tarfile.REGTYPE, tarfile.AREGTYPE))
```

Complete retained diff reviewed through PR #77 at `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`.

GNU tar 1.35 documentation identifies both `REGTYPE` and `AREGTYPE` as regular-file flags and says the legacy `AREGTYPE` value should be silently recognized as a regular file. The candidate aligns mmdebstrap's class selector with that behavior.

## Overlap review

- Linux Fieldwork unit 01 changes `TransformAction` regex grammar.
- Unit 15 changes transform/link/PAX semantics.
- Unit 16 changes hard-link dependency state after selection.
- No adjacent packet owns `TypeFilterAction` regular-class membership.
- A bounded 2026-08-01 search of the canonical Forgejo project, visible issue index, and web-indexed issue/pull-request results found no current item mentioning `REGTYPE`, `AREGTYPE`, NUL regular flags, or the equivalent `--type-exclude` defect.

Refresh the overlap search immediately before any authorized submission.

## Git transport limitation

Direct source materialization attempts from upstream, Salsa, GitHub, and Linux Fieldwork Git endpoints failed in this runtime at DNS resolution. Representative results:

```text
fatal: unable to access 'https://salsa.debian.org/debian/mmdebstrap.git/': Could not resolve host: salsa.debian.org
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
```

Current source identity and content were obtained through the official project web source and the connected Linux Fieldwork repository. No complete local upstream checkout is claimed.

## Hosted integration state

Draft PR #410 carries the native assets and exact-source gate. The current workflow run is queued. A queued run is not a test result; no new hosted success is claimed until the exact-head job completes and its steps/logs are reviewed.

## Cleanup state

- Local semantics probes used temporary directories and removed all archive/extraction state automatically.
- The native shell test uses `mktemp -d` with an EXIT/HUP/INT/TERM cleanup trap.
- The Python exact-source gate uses `TemporaryDirectory` and executes the candidate twice in the same cleaned candidate tree.
- No mounts, sockets, containers, package installations, background processes, credentials, or upstream resources were created.
- Failed clone targets contain no successful checkout.

## Tests still pending

1. Complete draft PR #410 exact-head CI and review raw first-failure evidence if it fails.
2. Run the native asset through the real upstream `coverage.py` path with shellcheck and shfmt available.
3. Materialize the complete upstream repository at `77ec9be5417ee44c96343d2347145585da1b1f94`.
4. Verify commit, `tarfilter` blob, native test mode, and clean worktree.
5. Apply the source/test/registry patch with zero fuzz and zero offsets.
6. Run `tarfilter-regular-type-class` through the upstream runner on baseline and candidate.
7. Run the relevant broader tarfilter/project gate, clean the checkout, and rerun the focused candidate test.
8. Compose with adjacent tarfilter candidates for one complete-gate compatibility run.
9. Review the complete final upstream diff and refresh active overlap.

No complete-checkout native-suite, complete `coverage.sh`, package-build, or public-upstream CI result is claimed by this packet.
