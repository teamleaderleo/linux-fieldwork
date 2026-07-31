# Unique unittest discovery authority

## TL;DR

Default `unittest` discovery reruns inherited `test_*` methods in every discovered subclass. Three Linux Fieldwork extension classes add local cases without changing the inherited fixture for their parent tests, so repository CI repeats exact implementations and inflates the apparent evidence count.

This candidate adds an explicit repository runner that suppresses inherited methods only for those three classified exact-duplicate classes. It preserves locally declared and overridden tests, every non-policy test, discovery order, and the intentional tarfilter composition subclass whose candidate preparation actually changes.

## Explain like I'm five

A worksheet is copied into another folder and one new question is added. The old runner counts every copied question again. The new runner counts the original worksheet once and runs only the genuinely new extension question.

## Why care

Exact duplicate execution wastes hosted time, makes the suite total look broader than the unique evidence, and can obscure which fixture owns a failure. A smaller unique count is more truthful, not weaker.

The exact green predecessor CI for patch-validator PR #302 visibly ran inherited caching, LF-23, and tarfilter tests again under extension-class names. That validator is now merged into `main`; this unit turns the observed overcount into an explicit discovery policy on top of the merged default gate.

## Exact boundary

Owning issue: #314. Canonical PR: #315. Branch: `tooling/unique-unittest-discovery-review`.

Current-main base: merged patch-validator commit `e93b0353871dd29ebf9eda32245b2607f9572cc7`.

Changed surfaces relative to current `main`:

- `.github/workflows/linux-fieldwork-ci.yml`;
- `tools/run_fieldwork_unittests.py`;
- `tests/test_fieldwork_unittest_discovery.py`;
- this record.

## Classified exact duplicates

The local-method-only policy names:

- `test_caching_proxy_parent_swap_race.CachingProxyParentSwapRaceTest`;
- `test_lf23_cancellation_harness_symlink_safety.LF23CancellationHarnessSymlinkSafetyTest`;
- `test_tarfilter_transform_regex_python_group_controls.TarfilterTransformRegexPythonGroupControlsTest`.

These classes add local tests and use inherited setup or helpers, but their inherited parent methods execute the same source state and fixture as the already-discovered parent class.

## Intentional composition retained

`test_tarfilter_transform_regex_edge_cases.TarfilterTransformRegexEdgeCasesTest` remains outside the policy because it overrides `prepare_candidate()` and applies an additional patch. Its inherited parent tests exercise a different stacked source state and remain a real composition regression.

The caching parent-swap module's locally declared optimized-child matrix also remains. This policy changes ordinary repository discovery only; direct module behavior is unchanged.

## Candidate contract

`tools/run_fieldwork_unittests.py`:

- performs ordinary discovery from `tests/`;
- registers both repository and tests import roots;
- preserves unqualified sibling-test imports and `tools.*` package imports;
- flattens the suite while preserving discovery order;
- removes an inherited method only when its fully qualified class is in the explicit policy and the method name is absent from that class's `__dict__`;
- retains locally declared overrides and every non-policy test;
- fails closed if a policy class disappears;
- reports discovered, retained, and removed counts;
- supports execution, list-only, and JSON modes;
- returns the underlying unittest result.

Repository CI invokes:

```text
python3 -m tools.run_fieldwork_unittests --verbosity 2
```

Module execution preserves the repository root as an import path. The runner also inserts both required roots explicitly before discovery.

## Focused regression

`tests/test_fieldwork_unittest_discovery.py` discovers the actual repository suite without executing it and proves:

- every policy class is present;
- each policy class originally contains inherited methods beyond its local declarations;
- each filtered policy class contains exactly its locally declared `test_*` methods;
- the summary removal count equals the removed inherited methods;
- the intentional tarfilter composition class retains inherited contract tests;
- every non-policy test ID remains present and ordered;
- a stale policy entry raises `DiscoveryPolicyError`.

## Why a central runner

Module-level `load_tests` functions would alter direct module behavior and the caching optimized child, while distributing one repository evidence policy across unrelated test files.

The central runner limits the change to ordinary repository CI and keeps every exception and reason reviewable in one place.

## Complete-diff review

Review checked:

- policy class IDs match default unqualified discovery module names;
- repository and sibling import roots coexist;
- locally overridden methods remain callable and retained;
- flattened ordering preserves class and module fixture transitions;
- non-policy test instances and order are unchanged;
- missing policy classes fail before execution;
- list and JSON modes do not run tests;
- compilation and help gates include the runner;
- the merged changed-patch validator and its 19-control matrix remain intact.

No test body, candidate source, imported product source, external workflow, secret, live target, destructive action, or external interaction changes.

## Evidence boundary

This changes repository discovery authority and reported counts. It does not claim every retained test is behaviorally independent, deduplicate direct file execution, or automatically classify future subclasses.

A new class enters the policy only after showing that inherited methods use the same fixture and source state. A subclass that materially overrides candidate preparation remains a composition rerun.

## Evidence history

The unit was first tested as a one-commit stack on the exact PR #302 head. PR #302 then passed current-main CI and merged as `e93b035…`. The exact discovery workflow, runner, and focused-test blobs are now restacked as one commit directly on that merged main generation. A fresh exact-head current-main run is required because the evidence authority is the merged workflow composition, not the historical stack.

## Disposition

`REPAIR` until exact-head current-main Linux Fieldwork CI passes, reports the removed count, and every retained test succeeds.

A green unchanged head should move this internal repository tooling unit to `MERGE LOCALLY`.

## Authority

Internal Linux Fieldwork tooling only. No external contact is included or authorized.
