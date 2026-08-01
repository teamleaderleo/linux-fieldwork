# Handoff — unit 22 regular-file type class

Date: 2026-08-01  
Worker or variant: GPT-5.6 Thinking  
State: `HOLD`  
External contact authorized: `false`

## Exact repository state

- Linux Fieldwork repository: `teamleaderleo/linux-fieldwork`
- Branch: `upstream/unit-22-tarfilter-regular-type-class`
- Branch base: `main@6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact branch head immediately before this HANDOFF commit: `5bf2b8034fccf748129a9ee99dc2218db1f28d1f`
- Current branch head: the commit that creates this file; the issue #397 `UNIT CHECKPOINT` records its exact SHA after GitHub returns it.
- Packet: `upstream-packets/units/22-tarfilter-regular-type-class/`

A commit cannot embed its own SHA. The predecessor and branch are exact; use the checkpoint SHA or `git rev-parse upstream/unit-22-tarfilter-regular-type-class` for the creating commit.

## Exact upstream and candidate identities

- Canonical upstream: `https://salsa.debian.org/debian/mmdebstrap.git`
- Intended base branch: `master`
- Exact current upstream head: unresolved in this runtime
- Retained package tag: `debian/1.5.7-3`
- Retained resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Imported source path: `upstream/mmdebstrap/tarfilter`
- Imported source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Canonical Linux Fieldwork candidate PR: #77
- Retained candidate head: `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`
- Candidate merge commit: `4b9e24b0b20c1398dcae825310c6b7d0d5c273d0`
- Exact-head CI: run `30537313944`, success
- Retained patch: `patches/0001-tarfilter-treat-nul-as-regular.patch`
- Retained focused regression: `scripts/test_regular_type_class.py`
- Controlled Salsa fork: `NEEDS FORK`

## Completed work

1. Read issue #397, its packet protocol comment, `upstream-packets/README.md`, and `upstream-packets/INDEX.md`.
2. Confirmed unit 22 had no prior claim, packet, or branch.
3. Posted the internal claim for unit 22.
4. Read every linked carrier: issue #76 and comment, PR #77 metadata and review, all three PR changed files, imported source metadata, and imported tarfilter source.
5. Created the canonical branch from current Linux Fieldwork main.
6. Created the full required packet bundle.
7. Retained the one-line source patch and a self-contained archive-level regression.
8. Recorded the exact baseline/candidate/CI evidence and source ownership.
9. Documented rejected alternatives, adjacent-unit ownership, delivery path, authority boundary, and hold discriminator.
10. Drafted upstream issue and merge-request text without sending either.
11. Attempted a current upstream clone and recorded the exact failure.

## Latest distinguishing result

On imported source blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`, the baseline under `--type-exclude=REGTYPE` removes the `b"0"` member and retains the `b"\0"` member. On exact retained candidate head `e65989feaac9a9cb89c49fe536c26fe9e9ee8cb7`, selectors `REGTYPE` and `0` remove both regular encodings while a directory control remains; `DIRTYPE` remains independent. Linux Fieldwork CI run `30537313944` succeeded on that head.

## Hold blocker and discriminator

**Blocker:** the final upstream patch layer cannot be selected until active tarfilter units 01, 15, and 16 publish their final candidate heads/order, and an exact current Salsa checkout is available for rebase and native-test placement.

**Discriminator:** all of the following become available:

- exact current `master` commit and `tarfilter` blob;
- final adjacent tarfilter candidate heads/order;
- clean application or a resolved conflict;
- current native test location and focused command.

## First incomplete step

Run this in an environment with working Salsa Git access:

```sh
git clone https://salsa.debian.org/debian/mmdebstrap.git mmdebstrap-unit22
cd mmdebstrap-unit22
git rev-parse HEAD
git hash-object tarfilter
```

Immediately record both identities in `README.md`, `SOURCE_MAP.md`, `TESTS.md`, and this handoff before applying the patch.

## Next safe technical action

1. Refresh unit packets 01, 15, and 16 and record their exact final heads/order.
2. Clone exact current mmdebstrap `master` and record commit/blob identities.
3. Apply the retained patch with:

```sh
patch -p1 < /path/to/linux-fieldwork/upstream-packets/units/22-tarfilter-regular-type-class/patches/0001-tarfilter-treat-nul-as-regular.patch
```

4. Inspect current mmdebstrap tests and port `scripts/test_regular_type_class.py` into the native test owner.
5. Run baseline, candidate, relevant broader gate, cleanup, and immediate rerun.
6. Update the packet and decide `READY FOR AUTHORIZATION` versus a newly specific hold.

## Tests and gates still pending

- current Salsa base application;
- mmdebstrap-native focused regression;
- relevant tarfilter test group;
- package build or other project gate selected by current upstream conventions;
- cleanup and rerun on exact current candidate;
- final overlap review after adjacent tarfilter ordering.

## Cleanup state

- No successful Salsa checkout exists in `/mnt/data/mmdebstrap-unit22`.
- No mounts, sockets, containers, package installs, background processes, or credentials were created.
- GitHub branch and packet files are intentional retained state.
- No upstream fork, branch, issue, merge request, comment, review, email, or other contact was created.

## Authority

Internal Linux Fieldwork work and issue checkpoints are authorized. External contact remains unauthorized. Explicit authorization is required before creating or using an upstream fork for contact, opening a Salsa merge request, posting an issue/comment/review, or sending email.
