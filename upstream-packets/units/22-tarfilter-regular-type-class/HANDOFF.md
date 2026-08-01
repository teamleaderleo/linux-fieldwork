# Handoff — unit 22 regular-file type class

Date: 2026-08-01  
Worker or variant: GPT-5.6 Thinking  
State: `ACTIVE`  
External contact authorized: `false`

## Exact repository state

- Linux Fieldwork repository: `teamleaderleo/linux-fieldwork`
- Branch: `upstream/unit-22-tarfilter-regular-type-class`
- Branch base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact branch head immediately before this HANDOFF refresh: `15feb47bb73d6a7292e12340d9ac0886f15e4f80`
- Current branch head: the commit that updates this file; issue #397 checkpoint records the exact resulting SHA.
- Packet: `upstream-packets/units/22-tarfilter-regular-type-class/`

A commit cannot embed its own SHA. Use the issue checkpoint or `git rev-parse upstream/unit-22-tarfilter-regular-type-class` for the final handoff commit.

## Exact upstream and candidate identities

- Canonical upstream: `https://gitlab.mister-muffin.de/josch/mmdebstrap`
- Intended base branch: `main`
- Exact current upstream head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Current upstream defect: `TypeFilterAction` still maps `REGTYPE`/`0` only to `tarfile.REGTYPE`
- Current relevant source identity: matches imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, independently recorded by unit 15
- Debian package tag: `debian/1.5.7-3`
- Debian package resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Imported source path: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Canonical Linux Fieldwork candidate PR: #77
- Retained candidate head: `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`
- Candidate merge commit: `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Exact-head CI: run `30537313944`, success
- Retained patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Retained focused regression: `scripts/test_regular_type_class.py`
- Controlled upstream fork: `NEEDS FORK`

## State correction

The previous `HOLD` disposition was wrong. Missing native-test execution is technical work, and exact current upstream plus adjacent source ownership are now resolved. Unit 22 is `ACTIVE` until the current-upstream native regression, broader gate, cleanup/rerun, and complete-diff review are complete. It becomes `READY FOR AUTHORIZATION` only when those gates leave a human send/hold decision as the sole remaining step.

## Completed work

1. Read issue #397, its packet protocol comment, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`.
2. Confirmed unit 22 had no prior claim, packet, or branch.
3. Posted the internal claim for unit 22.
4. Read every linked carrier: issue #76 and comment, PR #77 metadata and review, all three PR changed files, imported source metadata, and imported tarfilter source.
5. Created the canonical Linux Fieldwork branch and full packet bundle.
6. Retained the one-line source patch and self-contained archive-level regression.
7. Recorded exact baseline/candidate/CI evidence and source ownership.
8. Drafted upstream issue and pull-request text without sending either.
9. Identified canonical current upstream as `josch/mmdebstrap` `main@77ec9be5417ee44c96343d2347145585da1b1f94`.
10. Confirmed the current upstream source still carries the defective selector mapping.
11. Identified the upstream-native individual-test command through `coverage.py`.
12. Re-read active units 01, 15, and 16. They own separate code paths and create no final-order blocker for unit 22.
13. Corrected `README.md`, `SOURCE_MAP.md`, `TESTS.md`, `DECISIONS.md`, and this handoff from `HOLD` to `ACTIVE` and from Salsa packaging identity to canonical Forgejo upstream identity.
14. Attempted source materialization from Git endpoints; DNS resolution failed before checkout.

## Latest distinguishing result

On imported/current relevant source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, the baseline under `--type-exclude=REGTYPE` removes the `b"0"` member and retains the `b"\0"` member. On exact retained candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`, selectors `REGTYPE` and `0` remove both regular encodings while a directory control remains; `DIRTYPE` remains independent. Linux Fieldwork CI run `30537313944` succeeded on that head. Current upstream `main@77ec9be5417ee44c96343d2347145585da1b1f94` still has the defective mapping.

## First incomplete step

Materialize the exact current upstream checkout in an environment with Git access:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap mmdebstrap-unit22
cd mmdebstrap-unit22
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git rev-parse HEAD
git hash-object tarfilter
git status --short
```

Record the exact tarfilter blob and clean status before applying the patch.

## Next safe technical action

1. Apply the retained patch with zero fuzz and zero offsets.
2. Convert `scripts/test_regular_type_class.py` into the current upstream native test owner and add its test name to `coverage.py` where appropriate.
3. Run the baseline focused test and retain its NUL-member leak.
4. Run the candidate focused test through the documented native command form:

```sh
CMD=./mmdebstrap ./coverage.py --dist unstable <unit-22-test-name>
```

5. Run the relevant broader tarfilter/project gate.
6. Clean the checkout and rerun the focused candidate test.
7. Compose with current adjacent tarfilter candidates for one compatibility run; no final ordering dependency exists.
8. Review the complete diff and active upstream overlap.
9. Move directly to `READY FOR AUTHORIZATION` when those technical gates pass.

## Tests and gates still pending

- exact upstream checkout materialization;
- clean patch application receipt;
- mmdebstrap-native focused regression;
- relevant broader tarfilter/project gate;
- cleanup and immediate rerun;
- composed adjacent-candidate compatibility run;
- complete current-upstream diff and overlap review.

## Cleanup state

- Failed clone targets contain no successful checkout.
- No mounts, sockets, containers, package installs, background processes, or credentials were created.
- GitHub branch and packet files are intentional retained state.
- No upstream fork, branch, issue, pull request, comment, review, email, or other contact was created.

## Authority

Internal Linux Fieldwork work and issue checkpoints are authorized. External contact remains unauthorized. Explicit authorization is required before creating or using an upstream fork for public contribution, opening a pull request, posting an issue/comment/review, or sending email.
