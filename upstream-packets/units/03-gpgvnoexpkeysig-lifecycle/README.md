# Unit 03 — mmdebstrap `gpgvnoexpkeysig` lifecycle

State: `READY FOR AUTHORIZATION`  
Priority-zero issue: #397, unit 03  
Worker or variant: `ChatGPT GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-03-gpgvnoexpkeysig-lifecycle`  
External contact authorized: `false`

## TL;DR

The composed lifecycle correction from PR #196 still applies to the current mmdebstrap helper without source edits. A new real-GnuPG fixture generates a historical expired key, signs APT-style `Release` metadata, proves the wrapper rewrites genuine `EXPKEYSIG` to `GOODSIG`, proves the baseline masks a genuine `BADSIG` exit as status 0, and proves the candidate preserves `gpgv` status 1. The same fixture completes an isolated local `apt-get update` through both wrappers and passes an immediate rerun with empty candidate temporary directories.

The technical packet is ready for the repository owner's send/hold decision. A controlled upstream fork and candidate branch still require explicit authorization.

## Accomplished behavior

The proposed wrapper validates every `--status-fd` occurrence before execution, preserves the verifier's exact ordinary result, rewrites only `EXPKEYSIG` status records, owns and reaps verifier and filter children, forwards wrapper-only HUP/INT/TERM, prevents filter failure from feeding SIGPIPE back into a live verifier, avoids duplicate replay after a late signal, and applies explicit verifier/filter/cleanup precedence.

## Why care

The current `gpgv | sed` pipeline reports `sed`'s status. A real invalid signature therefore produces `gpgv` status 1 while the wrapper returns 0. This helper sits on APT's signature-verification path and intentionally relaxes one expired-key status; unrelated verifier failures must remain visible.

## Scope

### Included

- `--status-fd` parsing and validation;
- real verifier status preservation;
- `EXPKEYSIG` to `GOODSIG` filtering on the selected descriptor;
- verifier/filter process ownership, signal forwarding, reaping, cleanup, and result precedence;
- current-upstream source identity and patch application;
- synthetic lifecycle evidence from PR #196;
- generated real-GnuPG expired-key and bad-signature controls;
- isolated local APT update through the wrapper.

### Excluded

- timeout or SIGKILL escalation for children that ignore forwarded signals;
- verifier-created descendant process groups;
- removal of inherited dynamic-fd `eval` redirection;
- live status streaming during verification;
- additional `/bin/sh` implementations beyond the existing `dash` evidence;
- public issue, pull request, email, comment, or package upload.

### Split boundary

The selected unit keeps parser, verifier status, filtering, signal ownership, and cleanup together because they share one wrapper state machine and overlapping source lines. Escalation policy, descendant process groups, and a rewrite away from shell remain separate future policy units.

## Exact identities

| Identity | Value |
| --- | --- |
| Upstream project | mmdebstrap |
| Canonical repository | `https://gitlab.mister-muffin.de/josch/mmdebstrap` |
| Intended base branch | `main` |
| Upstream base commit | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Helper's latest upstream commit | `59e5870e7b76cc25dc6cb7b34586451d4ec2a524` |
| Controlled fork | `NEEDS FORK` |
| Candidate source branch | `NEEDS BRANCH` |
| Candidate head | current upstream base plus retained patch; resulting helper blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed` |
| Linux Fieldwork branch | `upstream/unit-03-gpgvnoexpkeysig-lifecycle` |
| Linux Fieldwork starting base | `6cc74d846c50b9bbb88247e8a128b67e8c174c1e` |
| Linux Fieldwork stop head | recorded in `HANDOFF.md` and the unit checkpoint on #397 |
| Imported/local source identity | `upstream/mmdebstrap/gpgvnoexpkeysig`, blob `83370755454a1322bf6862751aab7381d175aa8b` |
| Retained patch identity | `investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch`, blob `a30b37ca1228df1d80fd7611d4a591549314aeb0` |
| Proposed destination | canonical mmdebstrap Forgejo repository |
| Delivery method | Forgejo fork and pull request; explicit authorization required |

## Canonical links

- Priority-zero unit: #397 unit 03
- Owning Linux Fieldwork issues: #41, #175, #176
- Canonical Linux Fieldwork composition: PR #196, merged as `65d4213393cf2b2d84c71a8b6a05fdad15396b9b`
- Focused predecessor PRs: #138, #177, #180
- Packet source map: [`SOURCE_MAP.md`](SOURCE_MAP.md)
- Deep dive: [`DEEP_DIVE.md`](DEEP_DIVE.md)
- Tests and receipts: [`TESTS.md`](TESTS.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Current handoff: [`HANDOFF.md`](HANDOFF.md)
- Upstream issue draft: [`UPSTREAM_ISSUE.md`](UPSTREAM_ISSUE.md)
- Upstream PR draft: [`UPSTREAM_PR.md`](UPSTREAM_PR.md)

## Current result

### Demonstrated

- Current upstream `main` points at `77ec9be5417ee44c96343d2347145585da1b1f94`; the helper has had no later source change after `59e5870e7b76cc25dc6cb7b34586451d4ec2a524`.
- The retained patch applies cleanly to source blob `83370755454a1322bf6862751aab7381d175aa8b` and produces blob `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`.
- Real GnuPG 2.4.7 emits `EXPKEYSIG` for the generated historical expired-key fixture; the candidate emits `GOODSIG` and returns 0.
- A tampered payload makes real `gpgv` return 1 with `BADSIG`; the baseline wrapper returns 0 and the candidate returns 1 while preserving `BADSIG`.
- Isolated `apt-get update` 3.0.3 succeeds against a local file repository whose `InRelease` is signed by the genuinely expired fixture key through both baseline and candidate wrappers.
- The complete fixture passes twice; candidate temporary directories are empty after direct verifier and APT runs.
- PR #196's synthetic lifecycle matrix covered parser forms, verifier results 0/1/2, filter and cleanup precedence, HUP/INT/TERM, launch-registration windows, late-filter replay, child reaping, cleanup, and immediate rerun.

### Still bounded

- The regular-file handoff buffers status until verifier completion.
- The interval between `mktemp -d` and final trap installation remains tiny and documented.
- Signal-ignoring children can delay exit because escalation policy is outside this unit.
- No controlled upstream fork or public carrier exists.

### Compatibility boundary

The wrapper remains POSIX `/bin/sh`, keeps the imported arbitrary numeric status-fd contract, keeps stdout and stderr separate from the selected GnuPG status descriptor, and changes only the ownership and result handling around the existing one-record rewrite.

## Candidate organization

One coherent pull request is preferred:

1. apply `0001-canonical-lifecycle.patch` to current upstream `main`;
2. add a compact upstream-appropriate real-GnuPG regression derived from `scripts/run-real-gpg-fixture.sh` and `fixtures/Release`;
3. describe the buffering and escalation boundaries in the pull-request body.

The focused PRs remain evidence records and should stay closed.

## Current disposition

`READY FOR AUTHORIZATION` — current-upstream application, the distinguishing real-verifier control, expired-key behavior, local APT integration, cleanup, and rerun have been demonstrated. The remaining action is a human send/hold decision and, if authorized, creation of the controlled fork and public pull request.

## Next human decision

Choose one:

- authorize creation of a controlled mmdebstrap fork/branch and preparation of the pull request; or
- hold the submission for an additional repair of the pre-trap temporary-directory interval.

## Authority

Internal reads, branch creation, testing, packet writing, and issue checkpoints were authorized. No Debian, mmdebstrap, GnuPG, APT, Forgejo, mailing-list, or other external contact was authorized or made.
