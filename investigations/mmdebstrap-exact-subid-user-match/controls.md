# Exact subordinate-ID matching controls

## TL;DR

Merged PR #92 fixed `/etc/subuid` and `/etc/subgid` account detection by comparing field 1 literally and exactly. This follow-up strengthens the proof and repairs the retained patch carrier:

- a username beginning with `-` remains an exact existing record, proving `grep --` prevents option parsing;
- the complete patched Debian testsuite passes `/bin/sh -n` after zero-fuzz patch application;
- the source fence rejects line insertion or deletion instead of comparing only the shared `zip()` prefix;
- the retained patch now declares the exact nine-line hunk it supplies.

Linux Fieldwork CI `30598944690` / 797 correctly rejected the previous carrier before behavioral execution. Its hunk header declared ten old/new lines while the body supplied nine, so GNU `patch` required fuzz 1. Repair commit `69073f20a7f044bb05d5dc5c787d8be2e9a8f775` changed the header from `-153,10 +153,10` to `-152,9 +152,9`; PR #291 carries that repair on current-main branch `restack/mmdebstrap-exact-subid-proof-current-main-v3`.

## Explain like I'm five

The fix asks a list whether a person already has an entry. A name beginning with `-` can look like a command option unless the command uses an explicit options boundary.

```text
file entry: -debci:200000:65536
requested user: -debci
candidate action: grep -Fxq -- -debci
required result: existing entry is found; no duplicate is appended
```

The proof instructions also have to fit the exact source. The old instruction card said its replacement block covered ten lines while it actually contained nine. Approximate patching hid that bookkeeping error; zero-fuzz application exposed it.

## Why care

The merged source already contains `--`, while the original regression never executed a leading-hyphen identity. A source assertion can survive while option handling or quoting changes elsewhere.

The earlier diff check used ordinary `zip()`. A malformed carrier could remove or add trailing lines and `zip()` would silently ignore the unmatched tail. A test claiming “only two conditions changed” must reject every insertion, deletion, and unexpected replacement.

Patch packaging is part of the proof. A patch that needs fuzz can bind to neighboring source after drift and make a green test certify a candidate different from the reviewed diff.

## Question

Do the merged exact-account conditions preserve literal leading-hyphen identities, leave the full Debian testsuite syntactically valid, change exactly the intended two source lines, and apply with zero fuzz to the exact imported source?

## Source

- merged product carrier: PR #92;
- completed issue: #80;
- retained product patch: `0001-match-subid-user-field-exactly.patch`;
- executable matrix: `tests/test_mmdebstrap_subid_account_match.py`;
- stale proof carrier: PR #218, exact head `cde9d361d659357527d2c06a634b42c5b8070169`;
- stale-head gate: Linux Fieldwork CI `30581822309`, success;
- first zero-fuzz gate: `30598944690` / 797, failed at patch application as intended;
- repair commit: `69073f20a7f044bb05d5dc5c787d8be2e9a8f775`;
- current restack carrier and exact head: PR #291.

## Candidate

The repaired proof unit contains three files:

1. correct the retained patch hunk start/count while preserving the two source replacements;
2. run `/bin/sh -n` on the complete patched file;
3. add `-debci:200000:65536` as an exact-present case;
4. invoke the real patched block with `AUTOPKGTEST_NORMAL_USER=-debci`;
5. require byte-identical file content and status 0;
6. require candidate and baseline line counts to match;
7. compare with `zip(..., strict=True)` and require exactly two replacement lines;
8. require `patch --fuzz=0` and reject any fuzzy-application output.

The imported source remains unchanged.

## Reproduction

```sh
python3 -m unittest -v tests/test_mmdebstrap_subid_account_match.py
```

The matrix covers exact presence, substring collision, malformed delimiter-free input, regex-significant literal input, leading-hyphen identity, empty and absent files, subuid/subgid parity, immediate rerun idempotency, zero-fuzz patch application, complete shell syntax, and the full source-diff fence.

## Interpretation

**Established:** the first hardened gate found a malformed retained hunk before any behavioral result could be claimed.

**Candidate:** the corrected hunk applies exactly to the imported testsuite and preserves the same two intended replacements.

**Pending:** fresh exact-head repository CI and complete three-file review.

## Evidence boundary

This follow-up does not validate subordinate range overlap, numeric bounds, conflicting duplicate records, account-name policy, or allocation strategy. It creates no users, namespaces, mounts, packages, or persistent host state.

## Disposition

`REPAIR COMPLETE — EXECUTE EXACT HEAD`, then merge locally as durable proof and retire stale proof carriers.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
