# Individually green patches need a stack gate

## In simple words

Separate fixes can each pass while the combined source does not exist, does not apply, or changes behavior when the fixes interact. A repair programme needs an executable stack gate, not only one green branch per issue.

## What I learned

Patch correctness has at least three layers:

1. the isolated defect and regression;
2. textual composition with neighboring patches;
3. semantic composition of the resulting source.

Textual conflicts are obvious when hunks fail. Semantic conflicts are more dangerous because every patch can apply while one invariant invalidates another.

The `caching_proxy.py` work provided a concrete example. Atomic publication, response framing, and declared-length validation were tested independently. The response-framing control included a chunked response with a conflicting `Content-Length`. The isolated length candidate validated every present length. Combined naïvely, it would reject a valid de-chunked response using a length that transfer coding overrides.

## Do

- Define one canonical patch order or one combined source patch.
- Apply the full stack to the exact imported source in CI.
- Run the inherited negative and candidate contracts against that same source.
- Add interaction controls, not just the union of isolated tests.
- Record which canonical fixes are included and fail when one is omitted.
- Restack dependent candidates after a base changes semantically.
- Preserve compatibility properties repaired during review, such as file mode.
- Distinguish textual application failure from semantic interaction failure.

## Do not

- Do not call repository artifacts a repair stack merely because all files are present.
- Do not rely on green runs from branches based on superseded heads.
- Do not assume two patches commute because they touch different lines after manual rebasing.
- Do not let a later fix silently reintroduce an earlier permission, metadata, framing, cleanup, or authority defect.
- Do not prepare an upstream packet without a proven ordered series or combined diff.

## 🍩 Donut to avoid

**Green pieces, red stack:** every issue has a green test and a retained patch, but sequential application fails or the combined semantics violate one of the original contracts.

## Interaction questions

For every added patch, ask:

- Does it share an import/helper/source anchor with an existing patch?
- Does it change the representation another patch validates?
- Does it alter error timing, cleanup ownership, or publication timing?
- Does it change permissions, environment, framing, metadata, or status behavior outside its headline result?
- Does the dependent branch still contain the current base fix, or an earlier version?
- Is there a real source tree and exact-head run containing all canonical repairs?

## Validation

The Linux Fieldwork integration under `investigations/caching-proxy-core-stack/` composes atomic publication, permission compatibility, response framing, and corrected declared-length validation into one patch and one real-HTTP matrix.

## Environment and assumptions

The lesson applies to patch series, stacked pull requests, downstream distribution patches, backport queues, cherry-pick trains, and feature branches. It is not specific to unified diffs or Python.

## Limits

A stack gate cannot prove every interaction. It should prioritize shared source regions, representation changes, lifecycle boundaries, compatibility properties, and previously found regressions. Platform- and configuration-specific stacks still need their own execution environments.

## Related work

- Integration issue: #145.
- Investigation: `investigations/caching-proxy-core-stack/`.
- Atomic publication: #95 / PR #96.
- Response framing: #116 / PR #120.
- Declared-length validation: #101 / PR #103.
