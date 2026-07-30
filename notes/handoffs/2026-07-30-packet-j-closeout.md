# Packet J closeout and adjacent review record

Recorded: 2026-07-30

Repository base: `ca9d8547414423099471868be22174abf4caef6e`

## Authority

This work is internal Linux Fieldwork coordination, testing, and retained-artifact review. No Debian, Ubuntu, or other external issue, email, patch, merge request, comment, or review was created or authorized.

The already-open Debian bug #1135727 thread remains the sole existing external-contact exception.

## Packet J owner decisions

| Owner | Exact head | Decision | Result |
|---|---|---|---|
| PR #92 | `f105dac7bd78558eb0f938b269c6d97610d213bf` | ready for final human check | delimiter-free subordinate-ID records no longer count as account matches; focused four-test matrix and CI pass |
| PR #111 | `1e0dd57478b2ea31527d39983599e970f4b783f8` | merge locally | `ADAPTIVE_COORDINATION.md` remains the canonical contract; the field guide is its practical companion |
| PR #161 | `607e3b7c77aef393dfb322797f4dd636b18d1c8d` | merged | log classifier retained as main commit `07dea8b160f67af9d521ded72abfddb41e338490` |
| PR #142 | `d359a42932fda4f301306eed866cc2090cf3ff02` | merge locally | active libarchive fix is referenced instead of reimplemented |
| PR #32 | `0f0f7f1f98965e949df54ae38773175fb6dee635` | retire | duplicate contract and mandatory peer-review semantics conflict with consequence-based coordination |
| PR #71 | `8da2a44681cf588c81e31108b763b511a5568c1f` | retire | unique journal facts yielded to the canonical handoff |
| PR #72 | current `ff89c85712ebcd888cba15ebb803bf7f7134c032` | hold | current-sid broad carrier remains active only until its repaired artifact is classified |
| PR #187 | `d51348f6d1d76aa6930e24bef0e33066fb7916bb` | merged | canonical handoff retained as main commit `a254657636ca92302610cd4af4bc294fafa62bbd` |

Completed scout dispatch issues #10–#15 and handoff/cleanup issues #181–#183 were closed with owning receipts. PRs #32 and #71 were closed without merge.

The three unmerged landing candidates #92, #111, and #142 still produce clean merge trees against base `ca9d854`.

## PR #72 exact-artifact classification

### Historical head `10bc4f1`

Workflow `30551542868`, artifact `8765484385`, digest `sha256:0da65bdd591a7eac1fbac00215caebd371ad84379325940d0b5ea9a2307d6942` stopped at case 125/284 because the repository-relative `./mmdebstrap` proxy could not be resolved after the test changed directory. This is a reduction-harness path failure. The run did not reach the later hook-free phase.

### Replaced head `4146f5f`

Two exact-head reruns produced the same fatal boundary before any numbered case:

| Workflow | Artifact | Digest |
|---|---|---|
| `30577374058` | `8773708231` | `sha256:a795107dd94cb3ee9d36cfc7263e54c893b16209ae8f230999835be0b6edacd1` |
| `30577942543` | `8773918890` | `sha256:e08693f1a10bf5a08d9c5e7a57435ee3bd708337b0963da04c702bcbdc8bc895` |

Both runs passed repository tooling and Debian BTS capture. Their disposable sid containers built the mirror successfully and entered the first `coverage.sh --exitfirst` phase. Black then reported that the patched `coverage.py` would be reformatted, so testsuite status 1 became autopkgtest status 6.

The earlier `curl`-missing line is nonfatal in these artifacts: mirror creation continued and reported success. The fatal owner is the scheduling patch's redundant nested boolean parentheses.

PR #171 repaired the canonical patch at `b3576452edbac347890c4a54c6d3c4074b6555f7` and passed CI `30578896764`. PR #72 carries the same repair and formatting regression at `ff89c85712ebcd888cba15ebb803bf7f7134c032`. Workflow `30578966104` is the active privileged rerun. Until its artifact is classified, there is no evidence that the current head reaches `root-without-cap-sys-admin`.

The temporary installed-command proxy remains acceptable only for reduction. It changes source-preflight ownership and must not serve as proof that the installed package passes the original formatter, lint, and POD gates.

## Adjacent exact-head review

Merged PR #196 repaired the canonical `gpgvnoexpkeysig` lifecycle, but its final signal-race change left the retained patch header on predecessor blob `2ab2930`.

PR #200 synchronized the retained header and durable identities with the exact applied candidate:

- applied SHA-256: `a84aab13551311be70fb9d2875540888d52e8ab66d61a38ae41a005e10f8c8fb`;
- applied Git blob: `de7e0ae24218632fe2e32a1130f5c2a39f8c4aed`;
- exact head: `52c0abbddc499c2568b5347312753deb1a897b52`;
- CI: `30579185343`, success;
- merged main commit: `ca9d8547414423099471868be22174abf4caef6e`.

The new regression derives both identities from the applied bytes and requires the patch header and record to agree. It changes no candidate shell behavior.

## Remaining decisions

1. Classify PR #72 workflow `30578966104` at exact head `ff89c85`.
2. If the artifact reaches the named capability case, record its first product boundary and then retire the broad carrier or split only reusable tooling slices.
3. Land PR #92 after final human review and land PRs #111/#142 if their heads remain unchanged.
4. Keep all work repository-only unless a separate authority decision expands external contact.
