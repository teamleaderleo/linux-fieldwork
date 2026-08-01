# Current handoff

Updated: `2026-08-01`  
Worker or variant: `ChatGPT`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Linux Fieldwork packet base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork content head before this handoff update | `d52008e7e0297dae403177291ff913b43fd3b0c8` |
| Linux Fieldwork branch tip | this handoff commit; exact SHA is recorded in the unit checkpoint on #397 |
| Canonical upstream repository/branch | `josch/mmdebstrap`, `main` |
| Exact canonical upstream base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork | `teamleaderleo/mmdebstrap` |
| Fork legacy default branch | `master`, tip `574048f2a720057b75e56622003932f344dc700a`; unrelated Deepin packaging history, preserved |
| Controlled canonical base branch | `linux-fieldwork/upstream-main-snapshot` at `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled candidate branch | `linux-fieldwork/unit-15-tarfilter-transform-metadata` |
| Controlled candidate head | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Source commit | `f7833615824ad99023c21a495840d10f64c6401a` |
| Native-test commit | `f7337a7d2f33d280c8e5b1576dd729f4d076c13a` |
| Coverage-registration commit | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Baseline source | Git blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`; SHA-256 `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957` |
| Candidate source | Git blob `adb330efcc941bf5e646f195c245a3184e42f8e2`; SHA-256 `adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e` |
| Native test | `tests/tarfilter-transform-metadata`; Git blob `bc9fb4e0593df5a37dee986308ebb62abc4b6839`; SHA-256 `adab3852d9c8e719d64a24e1aed386d2eeccb45a43922f854d7458aa486f8caa` |
| Coverage registration | `coverage.txt`; Git blob `fdac8b9f86b04e48af6476c32b649b1ed4bda95a` |
| Retained packet patch | `patches/0001-tarfilter-transform-metadata.patch`; SHA-256 `4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c` |
| Native receipt | `artifacts/FORK_NATIVE_TEST.txt`; SHA-256 `74d0ceff423a8bbc57bd5e8ae4dff3aa6ba1cfc105ebdbfd47d717f9e20f33a1` |
| Packet matrix receipt | `artifacts/matrix-result.json`; SHA-256 `325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106` |
| Owning unit/carriers | #397 unit 15; parent #36; canonical composition PR #68 plus PR #102 |

## Current bounded claim

The controlled fork candidate is exactly based on canonical upstream commit `77ec9be5417ee44c96343d2347145585da1b1f94`, is three commits ahead and zero behind, and changes only `tarfilter`, one native test, and `coverage.txt`. The exact baseline loses the native test at the first-versus-global replacement discriminator. The exact candidate passes that native test twice, passes Python and POSIX shell syntax, matches GNU tar 1.35 for the retained replacement, target-scope, hard-link, PAX, and numeric matrix, and leaves no matching temporary state.

The claim ends before execution through the complete `coverage.py` runner, shellcheck, shfmt, package/build gates, hosted CI, broader platform coverage, and an upstream send decision.

## Work completed in this pass

- read the current Linux Fieldwork project instructions: `README.md`, `START_HERE.md`, `ADAPTIVE_COORDINATION.md`, and `FIELD_GUIDE.md`;
- refreshed issue #397, packet protocol, index, current unit packet, and linked carrier state;
- inspected the user-controlled fork and discovered that its legacy `master` is an unrelated packaging history with no common ancestor to canonical upstream;
- preserved legacy `master` and selected the existing `linux-fieldwork/upstream-main-snapshot` branch as the controlled canonical base;
- verified that the snapshot resolves exactly to canonical upstream `77ec9be5417ee44c96343d2347145585da1b1f94`;
- created controlled branch `linux-fieldwork/unit-15-tarfilter-transform-metadata`;
- committed the exact candidate source as `f7833615824ad99023c21a495840d10f64c6401a`;
- added native regression `tests/tarfilter-transform-metadata` as `f7337a7d2f33d280c8e5b1576dd729f4d076c13a`;
- registered the test in `coverage.txt`, producing final fork head `505bf81079a3b76c7d56bffa8097c1b5a494898e`;
- verified the fork comparison: three commits ahead, zero behind, exact three-file diff;
- reconstructed an exact baseline by reverse-applying the clean packet patch with GNU patch 2.8 and zero fuzz;
- ran the native test against baseline: status `1`, ending at `AssertionError: s/a/b/`;
- ran Python compilation and POSIX shell syntax checks against the candidate: both passed;
- ran the candidate native test twice: status `0`, `tarfilter transform metadata: PASS`, empty stderr both times;
- verified zero matching temporary directories after the rerun;
- classified absent shellcheck/shfmt and failed local GitHub DNS as tooling/environment boundaries rather than product failures;
- retained the exact native receipt and updated packet identities, source map, tests, decisions, and PR draft.

## Changed paths

### Controlled fork `teamleaderleo/mmdebstrap`

- `tarfilter`
- `tests/tarfilter-transform-metadata`
- `coverage.txt`

### Linux Fieldwork packet

- `upstream-packets/units/15-tarfilter-transform-metadata/README.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/SOURCE_MAP.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/TESTS.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/DECISIONS.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/UPSTREAM_PR.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/HANDOFF.md`
- `upstream-packets/units/15-tarfilter-transform-metadata/artifacts/FORK_NATIVE_TEST.txt`

## Latest distinguishing observations

1. **Fork history:** legacy `master` and canonical snapshot have no common ancestor. Preserving `master` avoids destructive replacement and keeps prior packaging history discoverable.
2. **Exact base:** `linux-fieldwork/upstream-main-snapshot` resolves to canonical upstream `77ec9be5417ee44c96343d2347145585da1b1f94`.
3. **Exact diff:** candidate head `505bf81079a3b76c7d56bffa8097c1b5a494898e` changes only three files: `coverage.txt` `+2`, `tarfilter` `+179/-23`, and the native test `+250`.
4. **Baseline discriminator:** the native test fails before later cases with `AssertionError: s/a/b/`, proving the old all-matches replacement behavior is still distinguished.
5. **Candidate result:** the native test passes twice with the exact fork source bytes.
6. **Recovery state:** no matching test temporary directories remain.
7. **Runner boundary:** direct native execution is complete; full `coverage.py` execution is not. Shellcheck and shfmt were unavailable.

## Gates completed

- controlled fork base identity;
- branch ancestry and exact fork head;
- complete changed-file boundary;
- exact source/test/coverage blob identities;
- clean forward and reverse patch application with GNU patch 2.8 and zero fuzz;
- baseline losing native regression;
- candidate native regression twice;
- Python compile check;
- POSIX shell syntax check;
- GNU tar replacement differential;
- target-scope differential;
- hard-link extraction and inode identity;
- long PAX path/linkpath regeneration;
- numeric occurrence differential and predecessor control;
- non-ASCII numeral rejection;
- cleanup and immediate rerun;
- public overlap recheck.

## Red or neutral runs classified

- local `git clone` of GitHub failed because the execution container could not resolve `github.com`: environment/network, not product behavior;
- baseline native test status `1`: expected losing control, not candidate failure;
- shellcheck: not installed, unexecuted gate;
- shfmt: not installed, unexecuted gate;
- complete `coverage.py` selected-test run: unexecuted;
- package/build and hosted CI gates: unexecuted.

## Cleanup state

All disposable test roots and Python `TemporaryDirectory` fixtures completed cleanup. The recorded `/tmp` scan found zero directories matching the native test prefixes. No process, socket, mount, container, image, package state, cache entry, or external project object remains under worker control.

Intentional retained state is limited to the controlled fork branch, Linux Fieldwork packet, patch, scripts, receipts, hashes, and internal drafts.

## First incomplete step

Run `tests/tarfilter-transform-metadata` through the complete upstream `coverage.py` path on exact fork head `505bf81079a3b76c7d56bffa8097c1b5a494898e`, with the repository's required mirror/cache state and formatting tools available.

## Next safe action

Use an environment that can fetch the controlled fork and install the test-runner dependencies:

```sh
rm -rf /tmp/mmdebstrap-unit15
git clone https://github.com/teamleaderleo/mmdebstrap.git /tmp/mmdebstrap-unit15
cd /tmp/mmdebstrap-unit15
git checkout --detach 505bf81079a3b76c7d56bffa8097c1b5a494898e

git diff --check 77ec9be5417ee44c96343d2347145585da1b1f94..HEAD
python3 -m py_compile tarfilter
sh -n tests/tarfilter-transform-metadata

# coverage.py requires shared/cache/debian/dists/unstable/InRelease.
# Prepare the repository's documented mirror state when it is absent.
test -e shared/cache/debian/dists/unstable/InRelease || ./make_mirror.sh

HAVE_QEMU=no CMD=./mmdebstrap \
  ./coverage.py tarfilter-transform-metadata
```

Then record:

- exact checkout head and dirty-state check;
- shellcheck and shfmt versions/results emitted by the runner;
- selected-test exit status and retained logs;
- cleanup and immediate rerun;
- whether the final internal three-commit form should be retained, squashed, or split for review.

If a complete mirror-backed environment is unavailable, the next smaller safe action is to run shellcheck and shfmt with the exact arguments shown in `coverage.py`, record their versions and diffs, and leave `coverage.py` explicitly open.

## Remaining blockers and decisions

- **Environment:** current execution container cannot resolve GitHub for `git clone`.
- **Fixture:** a complete checkout and `shared/cache/debian/dists/unstable/InRelease` are absent locally.
- **Tooling:** shellcheck and shfmt are absent locally.
- **Technical gates:** selected `coverage.py`, relevant package/build, and hosted CI remain.
- **Release organization:** final one-commit versus ordered-series form remains open.
- **Freshness:** recheck canonical upstream base and overlap immediately before any authorization decision.
- **Authority:** external contact remains unauthorized.

## External-contact state

`false; none occurred.`

The controlled fork branch and Linux Fieldwork issue checkpoint are internal repository coordination. No upstream issue, pull request, merge request, email, comment, review, release, or package upload was created.

## Files to read first on resume

1. `README.md`
2. `HANDOFF.md`
3. `TESTS.md`
4. `SOURCE_MAP.md`
5. `DECISIONS.md`
6. `artifacts/FORK_NATIVE_TEST.txt`
7. `artifacts/APPLICATION.txt`
8. controlled fork diff from `77ec9be5417ee44c96343d2347145585da1b1f94` to `505bf81079a3b76c7d56bffa8097c1b5a494898e`

## Do not repeat

- Do not rewrite or force-update the fork's legacy `master`; use the canonical snapshot branch.
- Do not recreate the controlled candidate branch; continue from `505bf81079a3b76c7d56bffa8097c1b5a494898e` unless canonical upstream has advanced.
- Do not revive PR #48's unchanged default symlink expectation.
- Do not use PR #52 as the canonical composition.
- Do not infer full GNU transform compatibility from this unit.
- Do not ship the historical PR #68 patch directly through GNU patch 2.8 without addressing its parser-hunk application failure.
- Do not use Python `str.isdigit()` for occurrence flags.
- Do not treat direct native execution as a completed `coverage.py` run.
- Do not rerun ad hoc source reconstruction when the controlled fork branch is fetchable.
- Do not contact upstream without explicit authorization.
