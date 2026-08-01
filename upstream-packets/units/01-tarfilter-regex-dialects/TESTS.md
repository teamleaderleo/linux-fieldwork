# Tests and evidence

## Exact retained inputs

| Input | Exact identity |
| --- | --- |
| Imported `tarfilter` | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Target-scope patch | blob `1703984aa0c030e5131618a3541ee85bfd68ec65` |
| Occurrence patch | blob `81828a468854e7ec9ef4cda9626b9c57314afba3` |
| Regex dialect patch | blob `2d7c457b83700d51b173efd0825128b6853a5f47` |
| Regex edge/parity patch | blob `9994ac2272f23872b7f6e00a20f7282cb9b8cce3` |
| Core test | blob `57409a8e727c237dcddbdf508be6e94dd57b326f` |
| Edge test | blob `3b45d959122dc8f4a630cf144f176ecdabe7d3fb` |
| Group-guard positive-control test | blob `5a7bbac729caf71be6033f71d792dfde0d5f653a` |
| Canonical product head | `4555c5c250c1afedb3947fd1a7b5a0323bd9d262` |
| Latest repaired grammar head | `55d20a4cc08c93b34961c679bdb73458fea4c408` |
| Internal repaired merge | `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` |
| Group-control proof head | `bb0a79dec47958c6b865d4b382a44baff17ab736` |
| Group-control proof merge | `ed49c01a85e9d363626db5d2973a33b67209e13b` |
| Current Debian archive source | `mmdebstrap 1.5.7-3` in sid/forky |
| Salsa release tag | `debian/1.5.7-3`, abbreviated commit `6fde9997` |

## Baseline/candidate matrix

| Case | Retained baseline | Candidate / GNU reference |
| --- | --- | --- |
| member `aaa`, `s/a+/b/` | returns `b` because Python activates `+` | remains `aaa` in GNU basic mode |
| member `aaa`, `s/a\+/b/` | direct-Python spelling diverges | returns `b` in GNU basic mode |
| `s/a+/b/x` | predecessor rejects `x` | extended mode returns `b` |
| GNU basic capture/backreference | predecessor fails | candidate matches GNU tar |
| Python `(?...)` groups in `x` mode | Python can accept and execute | candidate and GNU tar reject |
| `s/\(?/X/x`, `s/[(?]/X/x`, `s/\(/X/x` | an overbroad guard could reject | candidate and GNU tar produce `X` |
| malformed active intervals | Python can treat punctuation literally | candidate and GNU tar reject |
| unmatched extended `)` | Python rejects | candidate and GNU tar treat as literal when no group is open |
| repeated quantifiers | Python lazy/possessive/error semantics differ | candidate normalizes executed GNU nested cases |
| numeric occurrences and link targets | prerequisite composition required | candidate equals GNU tar per field |

## Retained Linux Fieldwork commands

From the Linux Fieldwork repository root:

```sh
LC_ALL=C python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
python3 -m py_compile \
  upstream/mmdebstrap/tarfilter \
  tests/test_tarfilter_transform_regex_candidate.py \
  tests/test_tarfilter_transform_regex_edge_cases.py \
  tests/test_tarfilter_transform_regex_python_group_controls.py
```

The tests require GNU tar and `patch`. They create disposable source trees and archives below `TemporaryDirectory`.

## Prior exact receipts

### Core and repaired candidate

PR #151 and issue #212 record the product evolution:

- branch-leading BRE `*`, literal `\0`, repeated quantifier, anchor, interval, occurrence, and link-target controls;
- active Python-only `(?...)` group rejection;
- canonical product head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`;
- exact-head CI `30579057679`, job `90994427063`, passed complete discovery;
- PR #216 repaired malformed active intervals and unmatched extended `)`;
- 23 GNU tar 1.35 differential tests passed twice on the repaired branch and twice on current-main synthetic merges;
- hosted exact-head CI `30581672669`, job `625`, passed repaired head `55d20a4cc08c93b34961c679bdb73458fea4c408`;
- cleanup and immediate focused rerun passed.

### Group-guard accepted neighbors

PR #220 records:

- exact proof head `bb0a79dec47958c6b865d4b382a44baff17ab736`;
- two proof files, 95 additions, zero product-source changes;
- hosted CI `30582215292` / 634 succeeded;
- direct 13-test inherited GNU differential suite passed twice;
- current-main focused suite passed 15/15;
- full `test_tarfilter_transform_regex*.py` discovery passed 38/38;
- Python compilation and `git diff --check` passed;
- merge commit `ed49c01a85e9d363626db5d2973a33b67209e13b`.

These receipts prove the retained internal composition and guard boundary. They do not prove current canonical Salsa `master`.

## 2026-08-01 source refresh

### Debian archive source

Observed official archive facts:

```text
source package: mmdebstrap 1.5.7-3
suites: sid, forky
Salsa release tag: debian/1.5.7-3 at abbreviated 6fde9997
tarfilter size in Debian Sources: 11,453 bytes
orig tarball MD5: 50febe17e2ac0aa0d4a2d24724e01629
```

A package-version mirror commit `574048f2a720057b75e56622003932f344dc700a`, described as updating mmdebstrap to `1.5.7-3`, carries `tarfilter` Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, equal to the Linux Fieldwork import.

Interpretation: the retained source aligns with the currently published Debian package generation. A direct Debian archive file digest and exact Salsa `master` blob remain unresolved, so this result is package-source corroboration rather than completion of the canonical rebase gate.

### Native test runner discovery

The published `1.5.7-3` README gives the full suite:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

It gives individual execution as:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable TEST-NAME
```

The published `coverage.py` stages:

```text
./tarfilter -> shared/tarfilter
```

and falls back to `/usr/bin/mmtarfilter` only when the source-tree file is absent. Therefore the current-source candidate must remain at `./tarfilter` while native tests run. The next worker should inspect `coverage.txt` and `tests/` from the exact Salsa checkout to select the narrow transform-related names, then run the relevant broader suite.

### Overlap refresh

Search date: `2026-08-01`.

- Debian BTS current package listing was searched for tarfilter transform and regex-dialect equivalents; no matching issue appeared.
- Web-indexed Salsa issue and merge-request searches returned no equivalent tarfilter regex carrier.
- Exact live Salsa inventory remains unverified because authenticated/raw canonical access was unavailable.

## Transfer and execution attempts in this continuation

### Local Git and archive transfer

Commands attempted included:

```sh
git clone https://github.com/teamleaderleo/linux-fieldwork.git
curl -fL --retry 2 \
  -o /mnt/data/mmdebstrap_1.5.7.orig.tar.gz \
  https://deb.debian.org/debian/pool/main/m/mmdebstrap/mmdebstrap_1.5.7.orig.tar.gz
```

Observed errors:

```text
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
curl: (6) Could not resolve host: deb.debian.org
```

Interpretation: connector and web reads succeeded, while the local execution runtime lacked DNS/source transfer. No source archive was downloaded, no patch command began, and no fresh test process ran.

## Exact next rebase procedure

On a runtime with Salsa and shell access:

```sh
git clone https://salsa.debian.org/debian/mmdebstrap.git mmdebstrap-unit-01
cd mmdebstrap-unit-01
git checkout master
git pull --ff-only
upstream_base=$(git rev-parse HEAD)
upstream_tarfilter_blob=$(git hash-object tarfilter)
printf 'base=%s\ntarfilter=%s\n' "$upstream_base" "$upstream_tarfilter_blob"
```

Record both identities before changing source. Then create a disposable candidate root with current `tarfilter` at `upstream/mmdebstrap/tarfilter` and apply:

```sh
candidate_root=$(mktemp -d)
trap 'rm -rf "$candidate_root"' EXIT HUP INT TERM
mkdir -p "$candidate_root/upstream/mmdebstrap"
cp /path/to/mmdebstrap-unit-01/tarfilter "$candidate_root/upstream/mmdebstrap/tarfilter"

patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch
python3 -m py_compile "$candidate_root/upstream/mmdebstrap/tarfilter"
```

If any prerequisite already exists or any hunk requires fuzz, offset, or manual placement, regenerate one coherent current-source diff. Record the exact upstream base, resulting file hash, complete diff, and conflict analysis before testing.

Adapt the Linux Fieldwork test helper so the focused matrix consumes the exact rebased candidate. Preserve the PR #220 positive-control test. Then place the rebased file as `./tarfilter` in the exact upstream tree and run the identified named native tests followed by the appropriate broader suite.

## Cleanup and rerun

This continuation created no successful checkout, temporary archive, patched source tree, process, socket, mount, container, or generated Python cache. A zero-byte or partial failed download was not retained. Durable state consists only of Linux Fieldwork packet commits and internal issue comments.

For the next execution:

1. delete the disposable candidate root and generated `__pycache__` directories;
2. verify the upstream checkout has only intentional candidate changes;
3. rerun the focused GNU matrix on the same exact candidate head;
4. rerun the selected native test command immediately;
5. record exit statuses and cleanup inspection.

## Gates completed

- [x] Canonical and predecessor carrier identities refreshed through PR #220.
- [x] Imported source and patch/test blobs pinned.
- [x] Retained baseline and candidate expectations reviewed.
- [x] Existing exact-head hosted receipts recorded.
- [x] Current Debian archive version, release tag, and source-file size recorded.
- [x] Upstream-native runner and candidate staging path identified.
- [x] Debian BTS and web-indexed Salsa overlap search refreshed.
- [x] Runtime transfer failures recorded verbatim.
- [ ] Exact current Salsa `master` base and `tarfilter` blob resolved.
- [ ] Four-patch state applied or regenerated without fuzz/offsets.
- [ ] Focused GNU differential matrix run on exact current-source candidate.
- [ ] Upstream-native focused tests run.
- [ ] Upstream-native broader test run selected and executed.
- [ ] Cleanup and immediate rerun completed.
- [ ] Complete current-source diff reviewed.
- [ ] Exact live Salsa issue/MR overlap searched.

## Tests omitted and reason

Fresh patch application and execution remain omitted because the runtime could not transfer the canonical source tree or Debian source archive into the shell environment. Historical CI and package-source observations are retained at their exact evidentiary level.
