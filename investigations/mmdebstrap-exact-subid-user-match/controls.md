# Exact subordinate-ID matching controls

## TL;DR

Merged PR #92 fixed `/etc/subuid` and `/etc/subgid` account detection by comparing field 1 literally and exactly. This follow-up strengthens the proof without changing the product patch:

- a username beginning with `-` remains an exact existing record, proving `grep --` prevents option parsing;
- the complete patched Debian testsuite passes `/bin/sh -n` after exact patch application;
- the source fence rejects line insertion or deletion instead of comparing only the shared `zip()` prefix.

The stale proof carrier PR #218 passed Linux Fieldwork CI run `30581822309` but later became non-mergeable. This current-main carrier preserves only its unique proof content.

## Explain like I'm five

The fix asks a list whether a person already has an entry. A name beginning with `-` can look like a command option unless the command uses an explicit “options stop here” marker.

```text
file entry: -debci:200000:65536
requested user: -debci
candidate action: grep -Fxq -- -debci
required result: existing entry is found; no duplicate is appended
```

The proof also compares the complete package-test script before and after patching. It must have the same number of lines and exactly two changed conditions.

## Why care

The merged source already contains `--`, but the original regression did not execute a leading-hyphen identity. A source assertion alone can survive while option handling or quoting changes elsewhere.

The earlier diff check used ordinary `zip()`. If a malformed carrier removed or added trailing lines, `zip()` would silently ignore the unmatched tail. A test claiming “only two conditions changed” must reject every insertion or deletion as well as unexpected replacements.

## Question

Do the merged exact-account conditions preserve literal leading-hyphen identities, leave the full Debian testsuite syntactically valid, and change exactly the intended two source lines?

## Source

- merged product carrier: PR #92;
- completed issue: #80;
- product patch: `0001-match-subid-user-field-exactly.patch`;
- executable matrix: `tests/test_mmdebstrap_subid_account_match.py`;
- stale proof carrier: PR #218, exact head `cde9d361d659357527d2c06a634b42c5b8070169`;
- stale-head gate: Linux Fieldwork CI run `30581822309`, success;
- current-main proof branch: `test/mmdebstrap-exact-subid-controls-current-main-v2`.

## Candidate

The follow-up modifies only the regression and this record:

1. retain the patched testsuite path;
2. run `/bin/sh -n` on the complete patched file;
3. add `-debci:200000:65536` as an exact-present case;
4. invoke the real patched block with `AUTOPKGTEST_NORMAL_USER=-debci`;
5. require byte-identical file content and status 0;
6. require candidate and baseline line counts to match;
7. compare with `zip(..., strict=True)` and require exactly two replacement lines.

The merged patch and imported source remain unchanged.

## Reproduction

```sh
python3 -m unittest -v tests/test_mmdebstrap_subid_account_match.py
```

The full matrix covers exact presence, substring collision, malformed delimiter-free input, regex-significant literal input, leading-hyphen identity, empty and absent files, subuid/subgid parity, immediate rerun idempotency, exact patch application, complete shell syntax, and the full source-diff fence.

## Interpretation

**Observed:** the merged patch spells `grep -Fxq --` for both files.

**Design choice:** retain executable identity and complete-diff controls rather than relying only on source text.

**Open question:** exact-head current-main CI must confirm the repaired proof before merge.

## Evidence boundary

This follow-up does not validate subordinate range overlap, numeric bounds, conflicting duplicate records, account-name policy, or allocation strategy. It creates no users, namespaces, mounts, packages, or persistent host state.

## Next step

The reviewer is deciding whether the two-file current-main proof is sufficient to merge locally after exact-head CI and complete diff review.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
