# Handoff — unit 01 tarfilter regex dialects

## Current state

State: `ACTIVE`  
Linux Fieldwork branch: `upstream/unit-01-tarfilter-regex-dialects`  
Branch base at claim: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`  
Commit immediately before this handoff: `e9ae74337173a6c56988c20c8562d9a12b38deca`  
Exact branch head containing this handoff: recorded in the current `UNIT CHECKPOINT` comment on issue #397  
External contact authorized: `false`  
External contact made: `none`

## Exact technical identities

### Canonical and package source

- canonical project: `https://salsa.debian.org/debian/mmdebstrap`
- intended base branch: `master`
- exact current canonical base: `UNRESOLVED`
- current Debian archive source: `mmdebstrap 1.5.7-3` in sid/forky
- Salsa release tag: `debian/1.5.7-3`, abbreviated commit `6fde9997`
- Debian Sources `tarfilter` size: `11,453` bytes
- imported Linux Fieldwork source: `upstream/mmdebstrap/tarfilter`
- imported source Git blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- package-version mirror commit: `574048f2a720057b75e56622003932f344dc700a`
- package-version mirror `tarfilter` blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- controlled upstream fork: `NEEDS FORK`
- upstream candidate branch: `NEEDS BRANCH`

### Product and proof carriers

- canonical product head: PR #151 `4555c5c250c1afedb3947fd1a7b5a0323bd9d262`
- product merge: `1a1952a78f79b2473f1f9513c1d5820f58987594`
- repaired grammar head: PR #216 `55d20a4cc08c93b34961c679bdb73458fea4c408`
- repaired grammar merge: `919ea3ed03e045f9a35b087549d76f4c0c5a9a0f`
- repaired hosted receipt: `30581672669` / job `625`, passed
- group-guard proof head: PR #220 `bb0a79dec47958c6b865d4b382a44baff17ab736`
- group-guard proof merge: `ed49c01a85e9d363626db5d2973a33b67209e13b`
- group-guard hosted receipt: `30582215292` / 634, passed
- proof execution: direct inherited suite twice; current-main focused 15/15; full regex discovery 38/38

### Ordered patch blobs

1. target scopes: `1703984aa0c030e5131618a3541ee85bfd68ec65`
2. numeric occurrences: `81828a468854e7ec9ef4cda9626b9c57314afba3`
3. regex dialects: `2d7c457b83700d51b173efd0825128b6853a5f47`
4. regex edge/parity: `9994ac2272f23872b7f6e00a20f7282cb9b8cce3`

### Focused test blobs

- core: `57409a8e727c237dcddbdf508be6e94dd57b326f`
- edge/parity: `3b45d959122dc8f4a630cf144f176ecdabe7d3fb`
- group-guard accepted neighbors: `5a7bbac729caf71be6033f71d792dfde0d5f653a`

## Completed across the unit branch

- read issue #397, its durable-workspace comment, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`;
- claimed unit 01 and created `upstream/unit-01-tarfilter-regex-dialects`;
- read owning issue #212 and the linked carrier chain through source prerequisites, review-discovered proof, and explicit boundary records;
- completed `CARRIER_AUDIT.md` covering issues #25, #28, #29, #36, #51, #63, #98, #108, #117, and #125; PRs #33, #48, #56, #68, #102, #113, #122, #135, #151, #202, #203, #211, #216, and #220;
- classified PR #202 as a duplicate repair and PR #203 as a superseded proof carrier;
- classified merged PR #220 as the canonical accepted-neighbor proof;
- kept issue #117/PR #122, issue #125/PR #135, and issues #28/#29/PR #33 outside unit 01 according to their explicit boundaries and issue #397;
- pinned exact source, patch, test, carrier-head, merge, and hosted-run identities;
- reviewed the executable patch order and baseline/candidate expectations in all three focused test modules;
- refreshed official Debian archive evidence for source version `1.5.7-3`, release tag `6fde9997`, and 11,453-byte `tarfilter`;
- verified a package-version mirror carries the same `tarfilter` Git blob as the Linux Fieldwork import;
- identified the upstream-native runner: `coverage.py` stages local `./tarfilter` as `shared/tarfilter`; README documents full execution through `coverage.sh` and individual execution through `coverage.py`;
- refreshed Debian BTS and web-indexed Salsa overlap searches; no equivalent tarfilter regex-dialect carrier appeared;
- attempted Git and Debian archive transfer into the local shell and recorded DNS failures verbatim;
- kept package-source corroboration separate from the unresolved exact canonical Salsa gate;
- updated `README.md`, `SOURCE_MAP.md`, `CARRIER_AUDIT.md`, `DEEP_DIVE.md`, `TESTS.md`, `DECISIONS.md`, `UPSTREAM_PR.md`, and this handoff.

## Latest distinguishing result

The current Debian package generation remains `1.5.7-3`, and a package-version mirror of that generation carries the exact Linux Fieldwork imported `tarfilter` blob. The complete internal proof chain is green through PR #220, including the three accepted neighbors of the active Python-group guard.

This advances source freshness, native-test knowledge, carrier completeness, proof completeness, and overlap evidence. The unit remains `ACTIVE` because exact current Salsa `master`, its `tarfilter` blob, and a fresh current-source candidate run remain unresolved.

## Exact transfer failures

Attempted commands:

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

Connector and web reads succeeded. The local shell environment could not transfer source bytes, so no patch command or fresh test process began.

## First incomplete step

On a runtime with canonical Salsa and shell access, execute:

```sh
git clone https://salsa.debian.org/debian/mmdebstrap.git mmdebstrap-unit-01
cd mmdebstrap-unit-01
git checkout master
git pull --ff-only
upstream_base=$(git rev-parse HEAD)
upstream_tarfilter_blob=$(git hash-object tarfilter)
printf 'base=%s\ntarfilter=%s\n' "$upstream_base" "$upstream_tarfilter_blob"
```

Immediately record both outputs in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff before changing source.

## Next safe technical action

1. Inspect exact current canonical `tarfilter`, `coverage.txt`, `tests/`, contribution instructions, issues, and merge requests.
2. Determine which PR #68 / PR #102 prerequisite behaviors already exist.
3. Apply the four-patch state to a disposable current-source copy with `patch --fuzz=0`, or regenerate one coherent current-source diff when context changed.
4. Preserve the PR #220 positive controls in the final regression.
5. Record every conflict, exact candidate file hash, complete diff, and candidate head.
6. Adapt the focused Linux Fieldwork harness to consume the exact current-source candidate.
7. Run Python compilation and the complete GNU differential matrix.
8. Keep the rebased candidate at upstream-tree `./tarfilter`; select exact transform-related native test names from current `coverage.txt` and `tests/`; run them through `coverage.py`.
9. Run the appropriate broader native suite, clean all generated state, and rerun focused commands immediately.
10. Review the complete diff and exact live Salsa overlap.
11. Leave the unit `READY FOR AUTHORIZATION`, `HOLD`, or `SPLIT` with one precise reason.

Do not create a Salsa fork, branch, issue, merge request, comment, review, email, or mailing-list post without explicit authorization.

## Commands to retain

From the Linux Fieldwork checkout, after placing exact current canonical `tarfilter` at `$candidate_root/upstream/mmdebstrap/tarfilter`:

```sh
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-target-scopes/tarfilter-transform-target-scopes.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-occurrence-selectors/tarfilter-transform-occurrence-selectors.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-dialects.patch
patch --fuzz=0 -p1 -d "$candidate_root" -i investigations/tarfilter-transform-regex-candidate/tarfilter-transform-regex-edge-cases.patch
python3 -m py_compile "$candidate_root/upstream/mmdebstrap/tarfilter"
```

Regenerate against current source when any patch requires fuzz, offsets, or manual context placement.

Retained focused command after adapting the harness to the exact current candidate:

```sh
LC_ALL=C python3 -m unittest discover -s tests -p 'test_tarfilter_transform_regex*.py' -v
```

Native command pattern after selecting exact current test names:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable TEST-NAME
```

Published full-suite pattern:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh
```

## Cleanup state

No successful local checkout, source archive, temporary candidate tree, archive fixture, test process, socket, mount, container, or Python cache was created in this continuation. Failed network commands left no retained source artifact. Durable retained state is limited to Linux Fieldwork branch commits and internal issue #397 comments.

## Gates still open

- exact current canonical Salsa base and `tarfilter` blob;
- exact current-source candidate head;
- clean no-fuzz/no-offset application or regenerated diff;
- focused baseline failure and candidate pass on current source;
- upstream-native focused tests;
- appropriate broader native suite;
- cleanup and immediate rerun;
- complete current-source diff review;
- exact live Salsa issue/MR overlap search;
- controlled fork and compare URL;
- explicit authorization before external contact.

## Human decision state

No send decision is requested. Technical work remains. After all gates pass, request a unit-specific decision on creating a controlled Salsa fork and sending the prepared merge request.
