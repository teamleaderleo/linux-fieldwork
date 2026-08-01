# Current handoff

Updated: `2026-08-01 15:28 +08`  
Worker or variant: `GPT-5.6 Thinking`  
State: `READY FOR AUTHORIZATION`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-18-tarfilter-no-option-passthrough` |
| Linux Fieldwork head before this handoff commit | `52fa96139bbcea7372dacc699b71697179b8c0e2` |
| Linux Fieldwork final head | commit containing this `HANDOFF.md`; exact SHA is posted in the #397 `UNIT CHECKPOINT` |
| Source/test change head | `748f95cf0470d2c9ba96b8432c3cac7d2267aaeb` |
| Upstream base repository/branch | `https://gitlab.mister-muffin.de/josch/mmdebstrap`, `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Current upstream tarfilter commit | `87b9b385b38795c58bc13ffb33b8724bed27f7a0` |
| Imported source blob | `ad776167a8473d5d15dbe22e850f4f6db35cf278` |
| Linux Fieldwork patch blob | `44428ecf8d83a6edf2fca4f4da030129daacb13f` |
| Regression blob | `0b8a0e092a6dd2bf7481e077e7c7ec0f27b461bb` |
| Upstream-shaped patch blob | `9f856f389c7a991813dbe9d959edaf94c1155dec` |
| Patched `tarfilter` SHA-256 | `8fec7cf1b1c6e314714e9a0347a7485f41d176e5cbc2769904f10af84a07e4ac` |
| Candidate fork/branch | `NEEDS FORK — authorization required` |
| Linux Fieldwork patch | `investigations/tarfilter-no-option-passthrough/tarfilter-no-option-passthrough.patch` |
| Upstream-shaped patch | `patches/0001-tarfilter-restore-no-option-passthrough.patch` |
| Exact test receipt | `artifacts/2026-08-01-focused-regression.json` |
| Owning issue/PR | #29 / PR #46; priority-zero #397 unit 18 |
| Historical workflow | Linux Fieldwork CI `30534506273`, PASS on PR #46 head `8c8f45872e6eb2b4ea770e5753c6dc66347c8f56` |

## Current bounded claim

The current mmdebstrap `tarfilter` no-option guard is unreachable because `strip_components` always exists. The refreshed candidate cleanly selects the existing byte-copy path when all six modifying operation categories are inactive, preserves explicit numeric zero as no-operation, and keeps every active operation on the rewrite path.

## Work completed

- read #397, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, #29, #27, PRs #46, #33, #23, the investigation, reusable note, retained patches, regression, LF-14 sparse evidence pointers, and current upstream source;
- continued the canonical unit branch and packet;
- confirmed current upstream repository head and `tarfilter` file commit remain unchanged;
- retained the regenerated zero-fuzz Linux Fieldwork and upstream-shaped patches;
- reconstructed the exact source, patch, regression, and upstream-shaped patch from GitHub content blobs because the shell had no network DNS;
- recomputed and matched every Git blob identity before execution;
- ran the committed focused regression twice;
- compiled source and regression;
- applied the upstream-shaped patch with `--fuzz=0` and compiled the patched source;
- retained a compact JSON execution receipt;
- reviewed the complete `main...branch` diff;
- refreshed visible upstream issue and pull-request overlap evidence;
- updated the packet index and unit state to `READY FOR AUTHORIZATION`;
- kept all upstream issue/PR text as drafts only.

## Exact focused results

Environment:

```text
Python 3.13.5
tar (GNU tar) 1.35
GNU patch 2.8
```

First run:

```text
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
Ran 3 tests in 10.181s
OK
EXIT_STATUS=0
```

Clean rerun:

```text
python3 -m py_compile upstream/mmdebstrap/tarfilter tests/test_tarfilter_no_option_passthrough.py
python3 -m unittest -v tests.test_tarfilter_no_option_passthrough
Ran 3 tests in 8.617s
OK
RERUN_EXIT_STATUS=0
```

Upstream-shaped patch:

```text
patch --dry-run --fuzz=0 ...
checking file tarfilter
patch --fuzz=0 ...
patching file tarfilter
python3 -m py_compile tarfilter
UPSTREAM_PATCH_APPLY=PASS
```

## Coverage completed

- baseline gzip rewrite and compression-signature loss;
- byte identity for plain, gzip, bzip2, xz, and GNU PAX sparse archives;
- byte identity for explicit strip zero and ID-shift zero;
- active path, PAX, type, strip, transform, and ID-shift semantic controls;
- zero-fuzz application for both retained patch forms;
- compilation before and after patching;
- clean second execution;
- complete branch file-fence review;
- current visible upstream overlap search.

## Current upstream and overlap result

- canonical repository page showed `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`;
- `tarfilter` remained at file commit `87b9b385b38795c58bc13ffb33b8724bed27f7a0` with the same unreachable guard;
- the upstream issue index showed six open issues, all unrelated;
- targeted searches for tarfilter no-option, no-option passthrough, and byte-preserving copy behavior found no equivalent visible issue or pull request;
- visible pull-request search results included unrelated merged PR #44 only.

## Complete-diff result

Final pre-handoff comparison was 18 commits ahead and zero behind `main`, with 13 changed paths:

- one patch-context refresh;
- one focused regression expansion;
- one packet-index disposition update;
- ten unit packet/patch/receipt files.

No imported source, workflow, dependency, generated archive, or adjacent tarfilter semantic change is in the branch diff.

## Cleanup state

No processes, sockets, mounts, containers, or generated repository files remain. Both test runs used self-cleaning `TemporaryDirectory` fixtures. No `/tmp/tarfilter-no-option-*` directory remained after rerun. The standalone upstream-apply directory was removed by an EXIT trap.

## First incomplete step

Obtain an explicit human authorization decision for controlled-fork creation/use and upstream submission.

## Next safe action

Without authorization, stop here and preserve the packet.

After explicit authorization:

```text
1. create or identify the controlled mmdebstrap fork;
2. branch from exact upstream base 77ec9be5417ee44c96343d2347145585da1b1f94;
3. apply patches/0001-tarfilter-restore-no-option-passthrough.patch with --fuzz=0;
4. commit the one-file source change;
5. rerun the focused regression and py_compile in the fork checkout;
6. verify upstream main and overlap once more;
7. submit UPSTREAM_PR.md only under explicit contact authorization.
```

## Remaining boundaries

- authority: external contact and public fork use remain unauthorized;
- candidate publication: no controlled fork or fork-native commit exists yet;
- optional assurance: a complete Linux Fieldwork repository suite was not rerun in the network-isolated shell; historical full CI is green and the exact changed focused regression passed twice;
- overlap freshness: repeat immediately before any future submission.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `DEEP_DIVE.md`
4. `SOURCE_MAP.md`
5. `DECISIONS.md`
6. `artifacts/2026-08-01-focused-regression.json`
7. `UPSTREAM_PR.md`
8. #29 and PR #46

## External-contact state

`false; none occurred`. No public fork, upstream issue, pull request, comment, email, review, or patch submission was created.

## Do not repeat

- Do not revive #27 as a separate carrier; #29 owns the defect.
- Do not use PR #33's combined patch as unit 18's canonical proof; PR #46 superseded it.
- Do not accept the old patch hunk merely because `patch` exits 0; it applied with fuzz 2.
- Do not bundle active sparse rewriting, dotfile/path normalization, parent retention, transform dialect work, or PAX ID-shift repair into this unit.
- Do not treat a supplied transform as no-operation based on a particular archive's member names.
- Do not contact upstream or publish/use a public fork without explicit authorization.
