# Handoff

## Unit state

`HOLD`

Unit 09 has a one-line controlled-fork candidate, exact static validation, two positive current-sid executions, and a complete durable evidence record. The sole required blocker is canonical Forgejo byte/history access, including mailing-list-carried overlap review.

## Exact stopping point

- Linux Fieldwork branch: `upstream/unit-09-dev-ptmx-bsdutils`
- Linux Fieldwork base: `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Packet head immediately before writing this handoff: `4d4811b5302405b5f320f9517da44ef43ed95bbe`
- Final stopping head: resolve the branch ref after this handoff commit; issue `#397` checkpoint records that exact ref
- Packet: `upstream-packets/units/09-dev-ptmx-bsdutils/`
- State in `upstream-packets/INDEX.md`: `HOLD: canonical Forgejo byte/history review`
- Canonical repository: `josch/mmdebstrap` on Muffin Forgejo
- Canonical branch: `main`
- Advertised canonical head: `77ec9be5417ee44c96343d2347145585da1b1f94`
- External-contact state: unauthorized; internal work only

## Controlled implementation carrier

```text
repository: teamleaderleo/mmdebstrap
provenance: fork of deepin-community/mmdebstrap
base branch: master
base head: 574048f2a720057b75e56622003932f344dc700a
base tests/dev-ptmx blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
candidate branch: linux-fieldwork/unit-09-dev-ptmx-bsdutils
candidate head: 43082a6bc959e2d7cefae48f52e045cc90869287
candidate tests/dev-ptmx blob: fa93b4b845ff4927a72f258364bd920e8c7dc573
compare: one commit, one file, one insertion, one deletion
upstream pull request: none
```

The controlled GitHub branch is a valid Debian `1.5.7-3` source carrier. Its Deepin ancestry does not establish canonical Forgejo freshness.

## Candidate

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=bsdutils,gcc,libc6-dev,python3,passwd \
```

Retained direct-upstream patch:

```text
patches/0001-tests-include-bsdutils-for-dev-ptmx.patch
```

## Completed technical work

1. Read issue `#397`, packet protocol/index, and the full linked carrier chain: issues `#53` and `#84`; PRs `#82`, `#86`, `#89`, `#60`, and `#72`; unit-08 execution records; and later internal carriers created during this pass.
2. Claimed unit 09 and created `upstream/unit-09-dev-ptmx-bsdutils` from exact main `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`.
3. Verified historical ownership from Debian CI run `72574145`: the generated apt root omitted `bsdutils`, then failed on inner-root `script(1)`.
4. Verified the imported source and controlled fork share baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea`.
5. Created controlled fork candidate commit `43082a6bc959e2d7cefae48f52e045cc90869287` with exactly one dependency-line change.
6. Added the upstream-rooted retained patch and packet-specific exact-blob regression.
7. Corrected the first malformed packet carrier after run `30689859933` rejected its hunk envelope; zero package claim.
8. Passed exact packet validation at head `a4303b4bf3c02fb4acfc16337e53b68b08626862`, run `30690010699`.
9. Surveyed accessible GitHub repositories. None contains canonical commit `77ec9be5417ee44c96343d2347145585da1b1f94`; newer GitHub forks still carry the same baseline source blob after local divergence.
10. Searched publicly indexed canonical, Debian BTS, and mailing-list records for an equivalent `dev-ptmx`/`bsdutils` correction; none was found. Search coverage remains secondary to exact canonical history.
11. Built focused current-sid execution carriers and retained their preflight/composition failures as exact red controls.
12. Ran the candidate twice in separate disposable Debian sid containers and recorded positive root and unshare results.
13. Closed internal PR `#403` as superseded by the cleaner optional direct one-case carrier `#407`.
14. Updated `README.md`, `SOURCE_MAP.md`, `DEEP_DIVE.md`, `TESTS.md`, `DECISIONS.md`, `INDEX.md`, and this handoff.

## Latest distinguishing result

Current-sid execution and immediate rerun both passed with installed `mmdebstrap 1.5.7-3` and `bsdutils 1:2.42.2-2`.

### Run 30690241513

```text
execution head: 501c19c7147b2452350069fda5375c4cdbc7ab7c
artifact ID: 8815599405
artifact digest: sha256:bd97c229b886501d57d4618381d1a07e446f48f6c46e409e1915f7d8675e0b82
root: SUCCESS, 18 seconds
unshare: SUCCESS, 18 seconds
```

### Run 30690452822 — preferred application receipt

```text
execution head: 55b603aa9a819217c19055a7becc91cf4832f082
artifact ID: 8815724078
artifact digest: sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e
patch receipt: patching file tests/dev-ptmx
root: SUCCESS, 36 seconds
unshare: SUCCESS, 42 seconds
```

Across both runs:

- both inner `script -c` hooks printed `foobar`;
- copied apt logs contained no missing-command signature;
- `/tmp/test.c` and `/tmp/log` were removed;
- mmdebstrap removed every generated root;
- selected testsuite result: `PASS`.

The outer autopkgtest status `2` belongs to the unrelated skipped `hint-testsuite-triggers` control entry. See:

```text
artifacts/CURRENT-SID-DOUBLE-PASS.md
```

## Optional direct one-case carrier

Draft internal PR `#407`:

```text
branch: investigation/mmdebstrap-dev-ptmx-direct-sid
head: ff573bdd4ce1c822fad47218bff052fcc87126a4
Linux Fieldwork CI run: 30691203697
Direct sid run: 30691203699
status at stopping point: queued
```

This carrier seeds only sid `InRelease`, uses `https://deb.debian.org/debian`, selects `coverage.py --exitfirst --mode=root --variant=apt dev-ptmx`, and records explicit residual mount/file/process checks. It is supporting confirmation; the required dynamic pass/rerun is already complete.

## First incomplete required step

Obtain exact canonical Forgejo bytes and history for `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`, or a fresher verified head.

Then:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git log --all -- tests/dev-ptmx
git grep -n 'bsdutils,gcc,libc6-dev,python3,passwd' -- tests/dev-ptmx
git apply --check /path/to/0001-tests-include-bsdutils-for-dev-ptmx.patch
git apply /path/to/0001-tests-include-bsdutils-for-dev-ptmx.patch
git diff --check
git diff -- tests/dev-ptmx
```

Also inspect the canonical contribution/mailing-list history for equivalent or adjacent changes.

## Hold discriminator and next action

- Equivalent correction already present: record exact canonical commit/carrier and move unit to `RETIRED`.
- Dependency still absent and the patch applies with zero fuzz and zero offset: create or refresh a controlled canonical Forgejo fork branch, record exact base/candidate identities, and move unit to `READY FOR AUTHORIZATION`.
- Test intent, provider, or hook sequence changed: reopen the ownership analysis and update the candidate.

No additional Debian sid run is required for the current source generation. PR `#407` may supply a cleaner zero-status supporting receipt when runner capacity becomes available.

## Cleanup state

- Historical failed run: generated root removed.
- Current-sid run `30690241513`: both generated roots removed; test temporary files removed.
- Current-sid rerun `30690452822`: both generated roots removed; test temporary files removed.
- Controlled GitHub source commit changes one tracked file only.
- Packet regressions use temporary directories and leave no persistent root, mount, listener, package state, or process.
- Optional PR `#407` adds explicit residual mount/file/process checks and remains queued.

## Authorization boundary

No mmdebstrap or Debian upstream issue, pull request, merge request, comment, review, email, mailing-list post, or other external contact was created. A canonical fork branch and any external delivery require explicit authorization.
