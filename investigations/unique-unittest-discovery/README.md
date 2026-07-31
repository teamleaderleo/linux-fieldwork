# Unique unittest discovery authority

State: `current-main carrier — exact-head gate pending`

Owning issue: #314. Canonical PR: #315. Branch: `tooling/unique-unittest-discovery-review`.

## TL;DR

Default `unittest` discovery reruns inherited `test_*` methods in every discovered subclass. Three Linux Fieldwork extension classes add local cases without changing the inherited fixture or candidate state, so repository CI repeats exact implementations and inflates the apparent evidence count.

This candidate adds an explicit repository runner that suppresses inherited methods only for those three classified exact-duplicate classes. It preserves locally declared and overridden tests, every non-policy test, discovery order, and the intentional tarfilter composition subclass whose candidate preparation changes.

## Explain like I'm five

A worksheet is copied into another folder and one new question is added. The old runner counts every copied question again. The new runner counts the original worksheet once and runs only the genuinely new extension question.

## Why care

Exact duplicate execution consumes hosted time, inflates the reported evidence total, and can obscure which fixture owns a failure. The unique count should describe unique executions.

The exact green patch-validator CI visibly ran inherited caching, LF-23, and tarfilter cases again under extension-class names. This unit turns that observed overcount into an explicit repository discovery policy.

## Current-main boundary

Current-main parent: `404540e46b35df682f1fc006bdadf837aafb1752`.

The PR body owns the exact live head and workflow receipts.

Four changed surfaces:

- `.github/workflows/linux-fieldwork-ci.yml`;
- `tools/run_fieldwork_unittests.py`;
- `tests/test_fieldwork_unittest_discovery.py`;
- this record.

The workflow, runner, and focused-test blobs are transferred unchanged from predecessor head `a1aa1de2dc063c35e090474f3fd8240037ac7e49`. This record is refreshed for current `main` and the bounded cross-context review requirement.

## Classified exact duplicates

The local-method-only policy names:

- `test_caching_proxy_parent_swap_race.CachingProxyParentSwapRaceTest`;
- `test_lf23_cancellation_harness_symlink_safety.LF23CancellationHarnessSymlinkSafetyTest`;
- `test_tarfilter_transform_regex_python_group_controls.TarfilterTransformRegexPythonGroupControlsTest`.

These classes add local tests and reuse inherited setup or helpers. Their inherited parent methods execute the same source and fixture as the already-discovered parent class.

## Intentional composition retained

`test_tarfilter_transform_regex_edge_cases.TarfilterTransformRegexEdgeCasesTest` remains outside the policy because it overrides `prepare_candidate()` and applies an additional patch. Its inherited parent tests exercise a different stacked source and remain a real composition regression.

The caching parent-swap module's locally declared optimized-child matrix also remains. This policy changes ordinary repository discovery only; direct module behavior is unchanged.

## Candidate contract

`tools/run_fieldwork_unittests.py`:

- performs ordinary discovery from `tests/`;
- registers repository and tests import roots;
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

## Focused regression

`tests/test_fieldwork_unittest_discovery.py` discovers the actual repository suite without executing it and proves:

- every policy class is present;
- each policy class originally contains inherited methods beyond local declarations;
- filtered policy classes contain exactly their locally declared `test_*` methods;
- the removal summary equals the removed inherited methods;
- intentional tarfilter composition retains inherited contract tests;
- every non-policy test ID remains present and ordered;
- stale policy entries fail explicitly.

## Why a central runner

Module-level `load_tests` functions would alter direct module behavior and the caching optimized child, while distributing one repository evidence policy across unrelated test files.

The central runner limits the change to ordinary repository CI and keeps every exception and reason reviewable in one place.

## Cross-context review receipt

- discovery identity → parent method versus inherited subclass instance → exact class and `__dict__` test;
- fixture lifecycle → module/class ordering → flattened suite order preserved;
- candidate identity → same source versus stacked source → intentional composition excluded from policy;
- future drift → renamed or removed class → fail-closed policy check;
- direct execution → repository CI versus module invocation → direct module behavior unchanged.

Stop reason: each selected context has an executable discriminator. Future subclasses remain outside the policy until separately classified.

## Evidence boundary

This changes repository discovery authority and reported counts. It does not claim every retained test is behaviorally independent, deduplicate direct file execution, or automatically classify future subclasses.

## Landing rule

1. exact current head is named in PR #315;
2. Linux Fieldwork CI runs through the new runner;
3. the log reports discovered, retained, and removed counts;
4. every retained test passes;
5. the direct diff remains these four files;
6. current-main drift receives review.

## Authority

Internal Linux Fieldwork tooling only. External contact authorized: false.
