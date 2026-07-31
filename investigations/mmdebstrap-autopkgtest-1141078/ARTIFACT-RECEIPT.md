# Exact receipt for the retained Packet B sid artifact

State: `completed receipt — focused case unresolved`

## TL;DR

The read-only receipt for Debian sid run `30641621084` passed and classified the exact retained artifact.

`root-without-cap-sys-admin` did **not** complete. Its only occurrence is an unresolved entry in the skipped-test inventory after the package testsuite had already failed. The first owned case failure was broad test `(242/284) chrootless`, followed by wrapper failure.

This artifact therefore cannot promote Packet B's focused hook-free scheduling claim. It does prevent a false claim that the focus case passed and routes the next package investigation to the broad `chrootless` failure or to a new focused execution that actually completes the case.

## Explain like I'm five

The long exam failed before the answer we care about was graded. The answer's name appears later on the list of unfinished questions, but there is no pass or fail mark beside it.

The receipt confirms the evidence box is authentic and says: do not count this as a pass; investigate the earlier failed question or run the focused question again by itself.

## Why care

Wrapper status 6 alone could mean:

- the focused case passed and something later failed;
- the focused case failed;
- the focused case never ran;
- the artifact belongs to another checkout.

The typed receipt distinguishes those outcomes without rerunning the roughly 50-minute package job.

## Exact source artifact

- source run: `30641621084`, attempt 1;
- source head: `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- generated merge checkout: `37648c5efd9cf80b5ae4ec063e8d6cb5b4f82d6e`;
- ordered parents: base `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`, head `fe49686c333aea3c5b8e378e655c52fa57e9224c`;
- artifact ID: `8799126060`;
- artifact name: `mmdebstrap-reproduction-gha-30641621084-1`;
- artifact digest: `sha256:33f972dfd71c08263a0d766d9e1ded96c11407f001315a2a0c23ae9d2bf68474`;
- artifact files: 36;
- script/container status: 6/6.

The raw artifact remains authoritative and expires on 2026-08-14 unless separately retained.

## Observed decision fields

Dedicated receipt run `30647516635` / 9 reported:

```text
focus_state=unresolved
focus_before_first_failure=False
focus_completed_before_first_failure=False
focus occurrence: line 17787, index 41/284, outcome null
first owned failure: broad chrootless case 242/284
wrapper failure line: 17747
```

The focus occurrence appears in the post-failure skipped inventory:

```text
(38/284) unshare-as-root-user-inside-chroot
(39/284) root-mode-inside-chroot
(40/284) root-mode-inside-unshare-chroot
(41/284) root-without-cap-sys-admin
(136/284) supply-components-manually
```

The earlier failure context is:

```text
rm -f /tmp/chrootless.tar /tmp/root.tar /tmp/before.md5 /tmp/before.tartv /tmp/after.md5 /tmp/after.tartv
test.sh failed
testsuite FAIL non-zero exit status 1
```

The final summary identifies failed test `(242/284) chrootless`.

## Receipt contract

`tools/summarize_mmdebstrap_reproduction.py`:

- locates every required artifact file by exact basename and rejects zero or multiple matches;
- rejects symlink and nonregular required paths;
- rebuilds the typed repository identity from retained input;
- requires `synthetic-merge-ref`, exact checkout/head/base, ordered parents, run ID, and attempt;
- requires raw revision-line agreement;
- requires script/container status and result-markdown agreement;
- reuses the canonical first-failure classifier;
- retains the first wrapper-failure line separately;
- records all focus occurrences, outcomes, and ordering booleans;
- retains bounded failure context, console tail, console digest, and phase-order receipt.

A nonzero package status is data. Malformed or contradictory evidence is what makes the receipt tool fail.

## Classifier repair carried with the receipt

The canonical classifier now:

- recognizes `test.sh failed` only while a named case is active;
- does not borrow a completed case for stray later text;
- avoids treating package/version inventories containing `perlcritic`, `pod2man`, `shellcheck`, or `shfmt` as failed preflight gates;
- recognizes native ShellCheck codes, native Black output, and explicit tool diagnostics;
- preserves the first event in transcript order.

Focused controls cover both losing and negative cases.

## Hosted workflow

The dedicated workflow has only:

- `contents: read`;
- `actions: read`.

It downloads the exact retained artifact, builds and prints the typed decision, and uploads only the derived JSON/stdout receipt. It does not run apt, autopkgtest, Docker, root operations, mounts, mirrors, or package installation.

Dedicated run `30647516635` succeeded and uploaded derived artifact `8800016944`, ZIP digest `sha256:0a804d0670adcb49a5d6c596646682d52767791b706be3eed24b6a0e3c024745`.

## Carrier history and failure ownership

The first receipt run rejected a manually transcribed checkout SHA. The artifact's typed identity and raw revision line supplied the corrected checkout.

Historical PR #371 then used a branch name that unintentionally activated the expensive package reproduction and Debian capture jobs. Its `lab-tools` job and dedicated receipt passed; the unrelated activated jobs failed. The canonical carrier is restacked on a neutral current-main branch so a read-only receipt no longer reruns the workload it exists to avoid.

## Packet B disposition

**HOLD FOR FOCUSED EXECUTION.** This retained broad artifact does not establish the focus case.

Next valid choices are:

1. run the focused hook-free case in a carrier that guarantees it actually executes and retains its own outcome; or
2. separately investigate the broad `chrootless` failure if it blocks the package matrix for independent reasons.

Do not use this artifact as evidence that `root-without-cap-sys-admin` passed, failed, or preserved hard-failure semantics.

## Evidence boundary

This unit interprets one exact retained artifact. It does not prove literal-head execution, current-main package behavior, source applicability, a product fix, or upstream acceptance.

The derived receipt preserves decision-changing fields and source coordinates, not the complete raw console.

## Authority

Internal Linux Fieldwork evidence only. No Debian, mmdebstrap upstream, external issue, email, release, deployment, or other public contact is included or authorized.

Owning issue: #370. Historical carrier: PR #371. Packet B context: #153 and #194.
