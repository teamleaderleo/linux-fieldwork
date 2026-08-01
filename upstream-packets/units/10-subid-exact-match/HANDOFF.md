# Current handoff

Updated: `2026-08-01 15:57 +08:00`  
Worker or variant: `GPT-5.6 Thinking`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-10-subid-exact-match` |
| Linux Fieldwork base | `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork packet parent | `5a9c462a23d6019d9fc92d61dcc4fee112bf1122`; the exact branch tip containing this self-referential handoff is recorded in the latest #397 checkpoint |
| User-controlled fork | `teamleaderleo/mmdebstrap` |
| Fork base branch | `master` |
| Fork base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Candidate branch | `linux-fieldwork/unit-10-subid-exact-match` |
| Candidate head | `eb75165459760cd4b9d8801147393bbde0535df6` |
| Candidate commit subject | `debian/tests: match subid account fields exactly` |
| Patch | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| Patch SHA-256 | `fc9c0c4d0552a80565a49a05f068934b3230b81703c9e0ed9c59d3307f9d544d` |
| Baseline file blob | `debian/tests/testsuite` Git blob `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Candidate file blob | `debian/tests/testsuite` Git blob `6925c7f05c3a5f050a4d3f89142085ff687ce3b0` |
| Owning issue/PR | #397 unit 10; issue #80; product PR #92; proof PR #291 |
| Exact source receipt | `artifacts/2026-08-01-exact-imported-source-gate.md` |
| Fork application receipt | `artifacts/2026-08-01-github-fork-application.md` |

## Current bounded claim

The package-test setup can mistake a substring or regular-expression match in another `/etc/subuid` or `/etc/subgid` record for an assignment belonging to `AUTOPKGTEST_NORMAL_USER`. The selected two-line correction parses field 1 and compares it literally and exactly with `cut -s -d: -f1 | grep -Fxq --`, while preserving the existing append value and test flow.

The user-controlled fork’s `master` file has the exact baseline blob already admitted by the full-source gate. Candidate commit `eb75165459760cd4b9d8801147393bbde0535df6` has the exact candidate blob already covered by complete shell syntax, Git whitespace/application checks, exact diff fencing, and the 18-case behavior/idempotency matrix. Focused package/user-namespace execution remains.

## Work completed in this pass

- identified the user-created fork as `teamleaderleo/mmdebstrap`;
- read fork `master` and confirmed `debian/tests/testsuite` blob `9f4eda87430da38b08a23a50a51e53b22cf7414b`;
- confirmed the fork base commit is `574048f2a720057b75e56622003932f344dc700a`;
- created candidate branch `linux-fieldwork/unit-10-subid-exact-match` from that exact base;
- committed the selected two-line correction as `eb75165459760cd4b9d8801147393bbde0535df6`;
- confirmed the candidate content blob is `6925c7f05c3a5f050a4d3f89142085ff687ce3b0`;
- confirmed the branch is one commit ahead, zero behind, with one changed file, two insertions, and two deletions;
- fetched the exact committed diff and verified it matches the packet candidate;
- checked GitHub combined status and found no attached status checks;
- attempted a read-only local clone; the execution container failed DNS resolution for `github.com` before repository access;
- recorded a durable fork-application receipt;
- updated `README.md` and this handoff to remove stale `NEEDS FORK` / `NEEDS BRANCH` state;
- made no contact with any upstream maintainer or upstream project.

## Changed paths in this pass

- `upstream-packets/units/10-subid-exact-match/artifacts/2026-08-01-github-fork-application.md`
- `upstream-packets/units/10-subid-exact-match/README.md`
- `upstream-packets/units/10-subid-exact-match/HANDOFF.md`

## Distinguishing observations

- The fork baseline blob is byte-identical to the baseline used by the prior exact-source gate.
- The fork candidate blob is byte-identical to the previously tested candidate bytes.
- GitHub’s compare result fences the candidate to one commit and one file with a 2/2 line replacement.
- No rerun of the exact-source matrix is required while baseline blob, candidate blob, and patch SHA remain unchanged.
- GitHub has no status checks attached to the candidate commit.
- The local clone failure is an execution-container DNS limitation; connector reads and writes established the repository, branch, commit, diff, and blob identities.

## Gates completed

- fork discovery and permission check: pass;
- exact fork base commit identification: pass;
- exact baseline file blob admission: pass;
- candidate branch creation: pass;
- candidate commit creation: pass;
- exact candidate file blob identity: pass;
- GitHub compare fence: pass, one commit ahead / zero behind / one file / 2 insertions / 2 deletions;
- exact committed diff inspection: pass;
- prior `git apply --check --whitespace=error-all`: pass on the identical baseline blob;
- prior `git am --keep-cr`: pass on the identical baseline blob;
- prior complete candidate `/bin/sh -n`: pass on the identical candidate blob;
- prior `git diff --check`: pass on the identical candidate blob;
- prior complete 18-case matrix: pass twice;
- GitHub combined status lookup: complete, no status checks present.

## Red or neutral runs classified

- PR #252 CI `30598944690` / 797: patch-packaging failure; product behavior unexecuted.
- Local clone of `teamleaderleo/mmdebstrap`: environment/DNS failure, `Could not resolve host: github.com`; no contradiction of connector-observed repository state.
- Empty GitHub combined status list: neutral; no CI result exists for candidate head.

## Cleanup state

The failed local clone left no usable repository and `/tmp/unit10-mmdebstrap-fork` contains no retained candidate state. No users, subordinate-ID records, namespaces, mounts, sockets, containers, packages, cache entries, or background processes were created.

Intentional retained state is the Linux Fieldwork packet, the fork application artifact, candidate branch `linux-fieldwork/unit-10-subid-exact-match`, and candidate commit `eb75165459760cd4b9d8801147393bbde0535df6`.

## First incomplete step

Run the focused package/user-namespace integration gate on candidate head `eb75165459760cd4b9d8801147393bbde0535df6`.

## Next safe action

From an environment that can clone the user-controlled GitHub fork:

```text
git clone https://github.com/teamleaderleo/mmdebstrap.git unit10-mmdebstrap
cd unit10-mmdebstrap
git checkout linux-fieldwork/unit-10-subid-exact-match
test "$(git rev-parse HEAD)" = eb75165459760cd4b9d8801147393bbde0535df6
test "$(git hash-object debian/tests/testsuite)" = 6925c7f05c3a5f050a4d3f89142085ff687ce3b0
/bin/sh -n debian/tests/testsuite
git diff --check master...HEAD
git diff --stat master...HEAD
git diff master...HEAD -- debian/tests/testsuite
```

Then use the existing disposable package-test harness and run the setup prelude plus the shortest ordinary-user namespace consumers first: `create-directory`, `unshare-as-root-user`, and `auto-mode-as-normal-user`. Preserve the first independent result. Add QEMU-only negative subuid cases only when that environment already exists.

## Unresolved blockers

- technical: focused package/user-namespace execution;
- environment: the current execution container cannot resolve `github.com` for a local clone;
- CI: candidate commit has no attached status checks;
- overlap: repeat the public issue/MR search immediately before any authorization request;
- authority: upstream contact remains unauthorized.

## Files to read first

1. `README.md`
2. `artifacts/2026-08-01-github-fork-application.md`
3. `TESTS.md`
4. `artifacts/2026-08-01-exact-imported-source-gate.md`
5. `SOURCE_MAP.md`
6. `DEEP_DIVE.md`
7. `DECISIONS.md`
8. issue #80, PR #92, and PR #291

## External-contact state

`No upstream contact occurred.` The user-controlled fork branch and candidate commit were created after the user directed work to continue in that fork. No upstream issue, pull request, merge request, email, comment, review, reaction, or other maintainer-facing action was created.

## Do not repeat

- do not rerun the exact-source matrix while baseline blob `9f4eda...`, candidate blob `6925c7...`, and patch SHA-256 `fc9c0c...` remain unchanged;
- do not replace candidate head `eb751654...` without recording the new exact diff and blob;
- do not restore PR #215, #218, #225, or #252 as the canonical carrier;
- do not remove `cut -s` without a replacement malformed-row policy and executable discriminator;
- do not combine this unit with runtime numeric UID/GID support, the `dev-ptmx` dependency fix, or the broad sid harness;
- do not open an upstream issue, pull request, merge request, email, comment, review, or reaction without explicit authorization.
