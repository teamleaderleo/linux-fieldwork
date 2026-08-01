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
| Latest repaired carrier head | `55d20a4cc08c93b34961c679bdb73458fea4c408` |
| Internal repaired merge | `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f` |

## Baseline/candidate matrix

| Case | Retained baseline | Candidate / GNU reference |
| --- | --- | --- |
| member `aaa`, `s/a+/b/` | returns `b` because Python activates `+` | remains `aaa` in GNU basic mode |
| member `aaa`, `s/a\+/b/` | direct-Python spelling diverges | returns `b` in GNU basic mode |
| `s/a+/b/x` | predecessor rejects `x` | extended mode returns `b` |
| GNU basic capture/backreference | predecessor fails | candidate matches GNU tar |
| Python `(?...)` groups in `x` mode | Python can accept and execute | candidate and GNU tar reject |
| malformed active intervals | Python can treat punctuation literally | candidate and GNU tar reject |
| unmatched extended `)` | Python rejects | candidate and GNU tar treat as literal when no group is open |
| repeated quantifiers | Python lazy/possessive/error semantics differ | candidate normalizes executed GNU nested cases |
| numeric occurrences and link targets | prerequisite composition required | candidate equals GNU tar per field |

## Retained execution commands

From the Linux Fieldwork repository root:

```sh
LC_ALL=C python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
python3 -m py_compile upstream/mmdebstrap/tarfilter tests/test_tarfilter_transform_regex_candidate.py tests/test_tarfilter_transform_regex_edge_cases.py
```

The tests require GNU tar and `patch`. They create disposable source trees and archives below `TemporaryDirectory`.

## Prior exact receipts

### Core candidate

PR #151 records the core candidate head `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`, internal merge `1a1952a78f79b2473f1f9513c1d5820f58987594`, and a focused GNU differential matrix that passed twice after patch-packaging repairs.

### Repaired candidate

Issue #212 and PR #216 record:

- 23 GNU tar 1.35 differential tests passed twice on the repaired branch;
- the same matrix passed twice on current-main synthetic merges;
- Python compilation and diff checks passed;
- caller-selected temporary roots and generated Python caches were removed;
- the focused tests passed again after cleanup;
- hosted exact-head CI run `30581672669`, job `625`, passed head `55d20a4cc08c93b34961c679bdb73458fea4c408`.

These receipts prove the retained internal composition. They do not prove a current canonical Salsa rebase.

## Work attempted in this session

### Repository checkout

Command:

```sh
git clone https://github.com/teamleaderleo/linux-fieldwork.git
```

Result:

```text
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
```

Interpretation: the local execution runtime lacked DNS access. No checkout, patch application, or test process began. The GitHub connector remained available for exact repository reads and writes.

### Current canonical upstream retrieval

Target:

```text
https://salsa.debian.org/debian/mmdebstrap
branch: master
file: tarfilter
```

Result: exact current commit and file bytes were unavailable through the active retrieval paths. A noncanonical GitHub mirror exposed a `tarfilter` blob equal to the retained imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; this equality is recorded only as old-base corroboration.

Interpretation: issue #397's exact current-upstream gate remains unexecuted. Reapplying patches to the already-tested imported blob would repeat old evidence and was deliberately skipped.

## Exact next rebase procedure

On a runtime with Salsa and shell access:

```sh
git clone https://salsa.debian.org/debian/mmdebstrap.git mmdebstrap-unit-01
cd mmdebstrap-unit-01
git checkout master
git pull --ff-only
upstream_base=$(git rev-parse HEAD)
printf '%s\n' "$upstream_base"
```

Then, from a Linux Fieldwork checkout, create a disposable candidate root with the current canonical `tarfilter` at `upstream/mmdebstrap/tarfilter` and apply the four patches in order with zero fuzz/offset tolerance. One reproducible form is:

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

If any prerequisite is already upstream or a hunk fails, regenerate one coherent current-source diff instead of accepting fuzz or offsets. Record the exact upstream base, resulting file hash, diff, and conflict analysis before running tests.

The retained LF tests currently read `upstream/mmdebstrap/tarfilter` from the LF checkout. After current-source regeneration, either update a packet fixture to the exact current base or add a test parameter/helper that runs the same matrix against the rebased candidate. Avoid silently substituting the old imported blob.

## Upstream-native test gate

After inspecting the current project test layout and contribution instructions, run the narrowest upstream entry points that exercise `tarfilter`, then the relevant broader test target. Record exact commands, environment, versions, exit statuses, and generated state. No upstream-native command is named here without inspecting the current canonical tree.

## Cleanup and rerun

This session created no local checkout, temporary archive, process, socket, mount, container, or generated cache because execution stopped at DNS/source retrieval. Durable state consists only of the Linux Fieldwork branch, packet files, and internal issue comments.

For the next execution, delete the disposable candidate root, verify no generated Python cache or archive remains, and rerun the focused matrix on the same exact candidate head.

## Gates completed

- [x] Canonical carrier identities refreshed.
- [x] Imported source and patch/test blobs pinned.
- [x] Retained baseline and candidate expectations reviewed.
- [x] Existing exact-head hosted receipt recorded.
- [x] Runtime retrieval failure recorded verbatim.
- [ ] Exact current Salsa base resolved.
- [ ] Four-patch state applied or regenerated without fuzz/offsets.
- [ ] Focused GNU differential matrix run on exact current-source candidate.
- [ ] Upstream-native focused tests run.
- [ ] Cleanup and immediate rerun completed.
- [ ] Complete current-source diff reviewed.
- [ ] Active upstream overlap searched.

## Tests omitted and reason

Every fresh execution gate remains omitted because this runtime could not obtain a local repository checkout or exact canonical upstream source. Existing CI is retained as historical exact-head evidence and is not promoted to current-upstream evidence.
