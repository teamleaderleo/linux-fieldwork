# Source map

## Canonical upstream identity

| Item | Repository path or URL | Exact revision | Notes |
| --- | --- | --- | --- |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` | repository head observed `77ec9be5417ee44c96343d2347145585da1b1f94` | Canonical Forgejo lineage; external contact remains unauthorized. |
| Primary implementation | `tarfilter`, `main()` id-shift block | file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0` | Current public source shifts `member.uid`/`member.gid` and retains stale numeric PAX keys. |
| Upstream test owner | `tests/tarfilter-idshift` | imported blob `6956e76aca153147d3a8a6668196d913ebc8a49e` | Owns xattr retention, zero-shift identity, ordinary shifting, extraction, and inverse-shift identity. |
| Test declaration | `coverage.txt`, `Test: tarfilter-idshift` | blob `87f4cccf5fc646c82600672113830419e20b95dd` | Declares `Needs-QEMU: true`. |
| Test dispatcher | `coverage.py` | blob `9a522484aef05deae514a98e4b6adf5feb6c886d` | Accepts the named test, copies local `tarfilter`, checks generated `shared/test.sh` with ShellCheck and shfmt, and selects the QEMU runner. |
| Suite wrapper | `coverage.sh` | blob `58e90568804db9f259b9ab99ce99ed74672fe2c5` | Checks `tarfilter` with Black, validates project shell files, requires mirror/QEMU preparation, and delegates to `coverage.py`. |
| Project instructions | `README.md` | blob `281e551bdf4af6e8336dca8a93cdf278a6be4cab` | Documents mirror preparation, the broad suite, and named test execution. |
| Debian package test | `debian/tests/testsuite` | blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` | Exports `HAVE_QEMU=no`; the named test is skipped in that package-test phase. |
| Package test dependencies | `debian/tests/control` | blob `58582587412629e180ba1712abd35b8d7f7bc7de` | Declares Black, ShellCheck, shfmt, Python, `libcap2-bin`, and suite dependencies. |
| Package source | Debian source `mmdebstrap` | `1.5.7-3` in sid/forky; `1.5.7-1+deb13u1` in trixie | Visible source lines retain the same id-shift behavior. |

Detailed project gate interpretation is in [`PROJECT_INSTRUCTIONS.md`](PROJECT_INSTRUCTIONS.md).

## Controlled repository and candidate

| Item | Exact identity | Classification |
| --- | --- | --- |
| Controlled repository | `teamleaderleo/mmdebstrap` | public GitHub package-source mirror; owner/admin/push access |
| Controlled default branch | `master` at `574048f2a720057b75e56622003932f344dc700a` | mirror lineage, not canonical Forgejo commit lineage |
| Candidate branch | `linux-fieldwork/unit-19-tarfilter-pax-idshift` | controlled writable branch |
| Candidate source commit | `1cd61501e18b5ffd861eceac9b70b1284fb0a0b6` | source correction |
| Candidate head | `07e89c68dbed198b04bb60aeb1947433f6ead0b0` | native test added after source commit |
| Compare state | ahead by `2`, behind by `0` relative to mirror `master` | clean branch fence |
| Candidate statuses | none attached when inspected | no CI receipt yet |

### Exact target-file identity

| Path | Controlled base blob | Packet/import blob | Candidate blob |
| --- | --- | --- | --- |
| `tarfilter` | `ad776167a8473d5d15dbe22e850f4f6db35cf278` | `ad776167a8473d5d15dbe22e850f4f6db35cf278` | `8c40acebba1734a26140790cfc59b72c62a98971` |
| `tests/tarfilter-idshift` | `6956e76aca153147d3a8a6668196d913ebc8a49e` | `6956e76aca153147d3a8a6668196d913ebc8a49e` | `cd749c063e754c4503771988fa1e5802076db0b0` |

The controlled repository exactly matches the packet for both target base files. It does not establish whole-tree equality with canonical head and cannot replace a canonical-lineage rebase receipt.

Full materialization evidence is in [`FORK_MATERIALIZATION.md`](FORK_MATERIALIZATION.md).

## Linux Fieldwork carriers

| Carrier | Exact head or merge | Role | Status |
| --- | --- | --- | --- |
| Issue #37 | closed 2026-07-30 | defect record, source analysis, reproducer, expected correction | canonical investigation |
| PR #78 | head `8d6443626e4338b180ec0533969bfe4d32b20d52`; merge `4df9ff80f01a0aef255e2c9011034d23e340cebe` | retained patch, exact-source regression, accepted review, CI receipt | prior reviewed candidate |
| CI run `30538012863` | PR #78 exact head | exact-source focused evidence | success |
| `investigations/tarfilter-pax-idshift/` | merged through PR #78 | prior narrative and Linux Fieldwork-path patch | historical evidence |
| `tests/test_tarfilter_pax_idshift.py` | merged through PR #78 | exact imported-source baseline/candidate regression | retained negative control |
| Unit 19 packet | `upstream/unit-19-tarfilter-pax-idshift` | patches, semantic probe, project gate map, fork receipt, drafts, decisions, handoff | current preparation owner |

## Candidate code

| File | Location | Change | Retained patch |
| --- | --- | --- | --- |
| `tarfilter` | immediately after validated `member.uid += args.idshift` and `member.gid += args.idshift` | remove stale `member.pax_headers["uid"]` and `["gid"]` | `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch` |

## Candidate test

| File | Fixture | Baseline failure | Candidate expectation |
| --- | --- | --- | --- |
| `tests/tarfilter-idshift` | PAX-large uid/gid member plus ordinary control | large member reads original IDs after `+7`; detector exits `1` with `large ownership was not shifted` | both shift; large PAX values regenerate; unrelated PAX data and payload survive; inverse shift restores IDs |

## Changed-file fence

Comparison of mirror `master...linux-fieldwork/unit-19-tarfilter-pax-idshift` reports exactly:

- `tarfilter`: `+2/-0`;
- `tests/tarfilter-idshift`: `+85/-2`;
- no other changed paths.

The intended canonical submission remains one commit containing those two files.

## Project-native gate

```sh
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

The named test must actually run with QEMU enabled. The generated test is checked using:

```sh
shellcheck --exclude=SC2050,SC2194,SC2016 -f gcc shared/test.sh
shfmt --posix --binary-next-line --case-indent --indent 2 --simplify -d shared/test.sh
```

A Debian autopkgtest configured with `HAVE_QEMU=no` skips this named test and is not the focused receipt.

## Patch artifacts

- source patch: `patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch`
- source patch SHA-256: `b86da5f6a2f2f1757b5b3fc0e32ebeabeeadbdebebb4cdc1961d3d1ff5eb3303`
- native test patch: `patches/0002-tests-cover-pax-idshift.patch`
- native test patch SHA-256: `ce5442b10be51b900a86947f25046ff39392fd2e9e9a776e982eabe79a177edc`

## Operation ownership map

| Operation | Before candidate | After candidate | Evidence |
| --- | --- | --- | --- |
| parse PAX numeric ownership | Python `tarfile` populates numeric fields and PAX strings | unchanged | forced-large fixture |
| validate negative shift | `tarfilter` | unchanged | validation remains before mutation and key removal |
| update numeric IDs | `TarInfo.uid`/`gid` mutation | unchanged | source block and ordinary control |
| choose output numeric metadata | stale input PAX strings override shifted fields | writer derives metadata from shifted fields after stale-key removal | packet probe, prior regression, native detector |
| retain unrelated PAX metadata | filtered PAX dictionary | unchanged except `uid`/`gid` | comment assertions |
| preserve payload | `tarfile.addfile()` | unchanged | payload assertions |
| focused execution | package test may skip QEMU-required case | explicit named QEMU run owns readiness receipt | project instruction map |

## Overlap and current upstream state

Search date: `2026-08-01`.

- Canonical repository head observed: `77ec9be5417ee44c96343d2347145585da1b1f94`.
- Canonical `tarfilter` still contains the uncorrected id-shift block.
- Indexed canonical issue/PR search found no equivalent active correction.
- Debian sid/forky source `1.5.7-3` retains the same behavior.

Recheck overlap immediately before authorization.

## Files deliberately outside scope

- path normalization and include/exclude logic: units 20/21;
- no-option passthrough: unit 18;
- transform, target, and general PAX path/link metadata: unit 15;
- type filtering and hard-link dependency handling: units 22 and 16;
- user/group names and unrelated PAX keys;
- shared imported files in Linux Fieldwork, which remain unchanged.