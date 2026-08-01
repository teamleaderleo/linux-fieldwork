# Handoff — unit 01 tarfilter regex dialects

## Current state

State: `ACTIVE`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
Branch base at claim: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`  
Commit immediately before this handoff: `d818bc02f074353ec942b58fe01b3ab512850d9e`  
Exact branch head containing this handoff: recorded in the unit checkpoint comment on issue #397  
External contact authorized: `false`  
External contact made: `none`

## Exact technical identities

- canonical project: `https://salsa.debian.org/debian/mmdebstrap`
- intended base branch: `master`
- exact current canonical base: `UNRESOLVED`
- imported Linux Fieldwork source: `upstream/mmdebstrap/tarfilter`
- imported source Git blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- repaired internal carrier head: `55d20a4cc08c93b34961c679bdb73458fea4c408`
- repaired internal merge: `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f`
- hosted exact-head receipt: run `30581672669`, job `625`, passed
- controlled upstream fork: `NEEDS FORK`
- upstream candidate branch: `NEEDS BRANCH`

Ordered patch blobs:

1. target scopes: `1703984aa0c030e5131618a3541ee85bfd68ec65`
2. numeric occurrences: `81828a468854e7ec9ef4cda9626b9c57314afba3`
3. regex dialects: `2d7c457b83700d51b173efd0825128b6853a5f47`
4. regex edge/parity: `9994ac2272f23872b7f6e00a20f7282cb9b8cce3`

Focused test blobs:

- core: `57409a8e727c237dcddbdf508be6e94dd57b326f`
- edge/parity: `3b45d959122dc8f4a630cf144f176ecdabe7d3fb`

## Completed in this session

- read issue #397, its durable-workspace comment, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`;
- confirmed no existing unit 01 workspace or branch;
- posted `CLAIMED — unit 01` on issue #397;
- created branch `upstream/unit-01-tarfilter-regex-dialects` from current `main`;
- read owning issue #212 and the canonical core/repair carriers PR #151, PR #202, and PR #216;
- read direct characterization/draft/prerequisite carriers PR #113, PR #211, PR #68, and PR #102;
- pinned exact source, patch, test, carrier-head, merge, and hosted-run identities;
- reviewed the executable patch order and baseline/candidate expectations in both focused test modules;
- verified a noncanonical mirror carries the same `tarfilter` Git blob as the retained import, solely corroborating the old base bytes;
- attempted local checkout and recorded the DNS failure verbatim;
- declined to repeat old-base tests because they would add no current-upstream evidence;
- created the complete unit packet: `README.md`, `SOURCE_MAP.md`, `DEEP_DIVE.md`, `TESTS.md`, `UPSTREAM_ISSUE.md`, `UPSTREAM_PR.md`, `DECISIONS.md`, and this handoff.

## Latest distinguishing result

The retained repaired head `55d20a4cc08c93b34961c679bdb73458fea4c408` has a green hosted receipt (`30581672669` / `625`) and prior 23-test GNU tar 1.35 differential reruns. This session established a complete, exact rebase manifest but produced no fresh current-source result because the canonical Salsa head was unavailable.

## Retrieval failure and interpretation

Attempted command:

```sh
git clone https://github.com/teamleaderleo/linux-fieldwork.git
```

Observed error:

```text
fatal: unable to access 'https://github.com/teamleaderleo/linux-fieldwork.git/': Could not resolve host: github.com
```

The GitHub connector supported repository reads/writes, but the local execution runtime lacked DNS. Exact current Salsa `master` also remained unavailable through the active retrieval paths. A mirror or package snapshot cannot satisfy issue #397's canonical-base gate.

## First incomplete step

On a runtime with canonical Salsa and shell access, execute:

```sh
git clone https://salsa.debian.org/debian/mmdebstrap.git mmdebstrap-unit-01
cd mmdebstrap-unit-01
git checkout master
git pull --ff-only
git rev-parse HEAD
git hash-object tarfilter
```

Immediately record both outputs in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff before changing source.

## Next safe technical action

1. Inspect current canonical `tarfilter`, tests, contribution instructions, issues, and merge requests.
2. Determine which PR #68 / PR #102 prerequisite behaviors already exist.
3. Apply the four-patch state to a disposable current-source copy with `patch --fuzz=0`, or regenerate one coherent current-source diff when context changed.
4. Record every conflict and the exact resulting diff/head.
5. Run Python compilation, the focused GNU differential matrix against the exact rebased candidate, current upstream-native entry points, cleanup, and immediate rerun.
6. Review the complete diff and current overlap.
7. Update drafts and leave the unit `READY FOR AUTHORIZATION`, `HOLD`, or `SPLIT` with one precise reason.

Do not create a Salsa fork, branch, issue, merge request, comment, review, email, or mailing-list post without explicit authorization.

## Commands to retain

From the Linux Fieldwork checkout, after placing the exact current canonical `tarfilter` at `$candidate_root/upstream/mmdebstrap/tarfilter`:

```sh
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch
python3 -m py_compile "$candidate_root/upstream/mmdebstrap/tarfilter"
```

Regenerate against current source when any patch requires fuzz, offsets, or manual context placement.

Retained old-base focused command:

```sh
LC_ALL=C python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
```

Adapt the harness so the fresh run consumes the exact current-source candidate. Avoid a hidden fallback to imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`.

## Cleanup state

No local checkout, temporary archive, patched source tree, process, socket, mount, container, or Python cache was created because execution stopped at source retrieval. Durable retained state is limited to the Linux Fieldwork branch, packet commits, and issue #397 internal comments.

## Gates still open

- exact current canonical Salsa base;
- exact current-source candidate head;
- clean no-fuzz/no-offset application or regenerated diff;
- focused baseline failure and candidate pass on current source;
- upstream-native focused and broader tests;
- cleanup and immediate rerun;
- complete current-source diff review;
- current active-equivalent-work search;
- controlled fork and compare URL;
- explicit authorization before external contact.

## Human decision state

No human send decision is requested yet. Technical work remains. After all gates pass, request a unit-specific decision on creating a controlled Salsa fork and sending the prepared merge request.
