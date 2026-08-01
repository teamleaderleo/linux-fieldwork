# Decisions

## 2026-08-01 — Claim unit 02 and create the canonical packet branch

Decision: use `upstream/unit-02-caching-proxy-complete-repair` and `upstream-packets/units/02-caching-proxy-complete-repair/`.

Reason: issue #397 and the packet index define these exact identities. No prior unit branch or workspace existed.

Supersedes: none.

Reopen trigger: only if issue #397 changes the unit boundary or canonical slug.

## 2026-08-01 — Treat PR #198 as the canonical internal source composition

Decision: use merged PR #198 final head `5e69cd25e62d0e86364459d97c9df8568ff84187` and merge `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f` as the complete mechanism carrier.

Reason: it deliberately composes the overlapping request, header, origin-status, framing, length, transfer-coding, publication, and late-error repairs in one generated source and passed exact-head CI.

Rejected alternative: restack the focused PRs mechanically. Their hunks overlap, and the chunked/declared-length interaction requires semantic reconciliation.

Reopen trigger: a current-upstream source change invalidates the composer anchors or changes a relevant protocol contract.

## 2026-08-01 — Prefer one upstream pull request

Decision: package source and upstream-native regression coverage in one Forgejo pull request, with one or two reviewable commits.

Reason: all source mechanisms share the same handler lifecycle, and their ordering carries correctness. Splitting independent submissions would recreate the integration gap described by issue #145.

Rejected alternative: an ordered public patch series. A series remains a fallback if upstream requests it, but the project provides a pull-request workflow and the candidate is one coherent behavior change.

Reopen trigger: upstream maintainers request a split or contribution guidance selects another delivery method.

## 2026-08-01 — Keep issue #227 outside unit 02

Decision: exclude same-UID parent-component replacement races.

Reason: the composed candidate provides pathname-level descendant validation. Race-proof confinement requires descriptor-relative traversal or an equivalent stronger design, with separate compatibility and platform review.

Rejected alternative: broaden the source patch now. That would delay the proven complete repair and combine two distinct authority models.

Reopen trigger: issue #227 produces a proven bounded repair that upstream explicitly wants combined before submission.

## 2026-08-01 — Preserve the narrow raw-path policy

Decision: retain rejection of every percent escape, literal backslash, NUL, empty component, dot component, doubled separator, and trailing separator.

Reason: the helper serves Debian archive paths and the internal matrix proves this subset. Decoding before cache-key selection aliases origin-distinct targets. Designing a complete injective escaped representation is larger work.

Rejected alternative: decode selected escapes. Partial decoding leaves ambiguity and replacement-decoding hazards.

Reopen trigger: current upstream tests or maintainer guidance demonstrate required percent-escaped archive paths and define an acceptable cache-key mapping.

## 2026-08-01 — Record current-upstream lineage without claiming byte equality

Decision: set upstream base to `77ec9be5417ee44c96343d2347145585da1b1f94`, record the visible file history and 4,439-byte Debian release cross-check, and leave exact Git-blob equality pending.

Reason: the canonical repository view identifies the head and shows no later `caching_proxy.py` change, while the current connector could not retrieve the raw file bytes from Forgejo. Evidence supports a likely clean rebase but does not justify a byte-match claim.

Rejected alternative: declare the imported blob current based only on filename history and size.

Clearing discriminator: `git hash-object caching_proxy.py` in an exact checkout of `77ec9be…` equals `e57a8516a0c76167894b05fc56be0e3165535488`.

## 2026-08-01 — Retain a reproducible exporter before retaining a patch

Decision: add `scripts/export_candidate.sh`, which invokes the merged composer, compiles the result, emits the source patch, and records hashes.

Reason: the execution environment had connector access to repository content but no mounted checkout or outbound DNS. A generated patch without executing the exact composer would be weaker than an exporter with an explicit unexecuted state.

Rejected alternative: hand-copy the composed source into a patch. That risks transcription drift and loses the canonical composer receipt.

Clearing discriminator: run the exporter in a full checkout, commit the generated patch and receipt, then rerun the complete matrix.

## 2026-08-01 — External contact remains gated

Decision: create no Forgejo issue, fork, branch, pull request, comment, review, email, or Debian submission.

Reason: issue #397 authorizes internal work only until explicit human authorization.

Reopen trigger: repository owner explicitly authorizes a named external action after exact-candidate gates pass.
