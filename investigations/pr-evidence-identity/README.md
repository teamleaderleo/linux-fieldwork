# Pull-request evidence identity

State: `first dual-checkout probe implemented — exact receipt pending`

Tracking: issue #342.

## TL;DR

A GitHub Actions workflow triggered by `pull_request` normally checks out a generated merge commit. Linux Fieldwork has often described a successful PR run as an exact-head gate even when the tested commit was the synthetic merge ref.

Both receipts are useful:

- `exact-head`: the checkout commit equals the declared pull-request head SHA;
- `synthetic-merge-ref`: the checkout commit equals the event SHA and has ordered parents `[base SHA, head SHA]`;
- `other-checkout`: the checkout fits neither identity.

This first probe checks out both the default generated merge and the literal head SHA, validates their Git identities, emits typed JSON receipts, and changes no repository state.

## Explain like I'm five

One test reads the proposed page alone. Another test temporarily inserts that page into the current book and reads the combined book. The receipt should say which object was tested.

## Why care

A merge-ref run proves integration with one base snapshot. A head run proves the proposed commit itself executes. Their expiration conditions differ:

- the head receipt changes when the branch head changes;
- the merge receipt changes when either the head or base snapshot changes.

Naming the tested commit prevents a base-side helper, workflow, or dependency change from being silently attributed to the branch head.

## Observed motivating receipt

PR #315 head `50ad8620436587910a5b18c4ffeb5ad8b7f8c121` passed workflow `30632898790` / 933. The workflow checkout log identified generated merge commit `51a62a9944a70cbbb25df517d7c7256f81c23646` from `refs/remotes/pull/315/merge`, based on `404540e46b35df682f1fc006bdadf837aafb1752` plus the proposed head.

That run is valid merge-ref integration evidence. Its receipt should name the generated commit and both parents.

## Four-file fence

- `.github/workflows/pr-evidence-identity-audit.yml`;
- this record;
- `tests/test_pr_evidence_identity.py`;
- executable `tools/audit_pr_evidence_identity.py`.

## Classifier contract

The tool accepts JSON with:

- checkout SHA;
- declared PR head and base SHAs;
- event SHA;
- ordered local parent SHAs;
- event, ref, branch, run, and attempt identity;
- optional expected classification.

It requires lowercase 40-hex SHAs, exact string and collection types, unique parents, positive decimal run identity, and branch refs for pull-request events. A commit cannot name itself as a parent.

Classification:

1. checkout equals declared head → `exact-head`;
2. checkout equals event SHA and parents equal `[base, head]` → `synthetic-merge-ref`;
3. otherwise → `other-checkout`.

An expected classification turns a mismatch into a fail-closed receipt error.

## Controls

The focused suite covers:

- literal head checkout;
- generated merge checkout;
- unrelated ordinary and two-parent checkouts;
- reversed merge parents;
- expected-mode mismatch;
- malformed, uppercase, short, boolean, duplicate, and self-parent identities;
- pull-request branch-ref requirements;
- ordinary versus optimized Python output and status parity.

## Workflow receipt

The dedicated workflow performs two independent checkouts:

```text
default pull_request checkout                  -> expected synthetic-merge-ref
ref: github.event.pull_request.head.sha        -> expected exact-head
```

It records `git rev-list --parents -n 1 HEAD` for each checkout, classifies both through the same tool, and uploads inputs, receipts, and raw Git lines.

Permissions remain `contents: read`.

## Instruction feedback

Use explicit names in landing records:

- **head gate** for code executed from the literal PR head SHA;
- **merge-ref gate** for code executed from the generated PR merge commit.

A carrier may require one or both. Every receipt should name tested commit, declared head, declared base, checkout classification, run, and attempt.

The generated merge result expires after base movement. The literal head result remains tied to its unchanged head but says nothing about newer-base integration.

## Cross-context review receipt

- event identity → `github.sha` versus declared PR head → both retained;
- Git topology → ordered base/head parents → exact parent check;
- checkout policy → default merge versus explicit SHA → dual checkout;
- runtime mode → ordinary versus optimized Python → parity control;
- authority → observation versus mutation → read-only workflow and artifacts.

Stop reason: the first live run can distinguish both checkout identities. Broader workflow policy waits for that receipt.

## Evidence boundary

The probe classifies commit identity only. It does not establish technical correctness, freshness, mergeability, changed-file scope, workflow-code provenance, or whether every carrier needs both modes.

## Authority

Internal Linux Fieldwork Git and Actions metadata only. External contact authorized: false.
