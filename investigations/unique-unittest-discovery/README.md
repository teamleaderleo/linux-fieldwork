# Unique unittest discovery authority

## TL;DR

Default `unittest` discovery reruns inherited `test_*` methods in every discovered subclass. Three Linux Fieldwork extension classes add local cases without changing the inherited fixture for their parent tests, so repository CI repeats exact test implementations and inflates the apparent evidence count.

This candidate introduces an explicit repository runner that suppresses inherited methods only for those three classified exact-duplicate classes. It preserves locally declared and overridden tests, all non-policy tests, class/module fixture ordering, and the intentional tarfilter composition subclass whose candidate preparation actually changes.

## Explain like I'm five

A worksheet is copied into another folder and one new question is added. The old runner counts every copied question again. The new runner counts the original worksheet once and runs only the genuinely new question from the extension folder.

## Why care

Exact duplicate execution:

- wastes hosted time;
- makes suite totals look broader than the unique evidence;
- can obscure which fixture owns a failure;
- encourages reviewers to read a larger number as stronger coverage when no new behavior was exercised.

A reduced count is more truthful, not weaker.

## Exact boundary

Owning issue: #314. Branch: `tooling/unique-unittest-discovery`.

This unit is stacked on PR #302 exact head `24cba1bffeaefb461d61abfede991aec8328ef83` because both units modify `.github/workflows/linux-fieldwork-ci.yml`. PR #302 owns changed patch-carrier validation; this unit owns unittest discovery. The mechanisms are otherwise independent.

Changed surfaces relative to PR #302:

- `.github/workflows/linux-fieldwork-ci.yml`;
- `tools/run_fieldwork_unittests.py`;
- `tests/test_fieldwork_unittest_discovery.py`;
- this record.

## Observed duplicate classes

The explicit local-method-only policy names:

- `test_caching_proxy_parent_swap_race.CachingProxyParentSwapRaceTest`;
- `test_lf23_cancellation_harness_symlink_safety.LF23CancellationHarnessSymlinkSafetyTest`;
- `test_tarfilter_transform_regex_python_group_controls.TarfilterTransformRegexPythonGroupControlsTest`.

In each class, the locally added tests use inherited setup and helpers, but the inherited parent test methods execute the same source state and fixture as their already-discovered parent class.

## Intentional composition retained

`test_tarfilter_transform_regex_edge_cases.TarfilterTransformRegexEdgeCasesTest` remains outside the suppression policy.

That subclass overrides `prepare_candidate()` and applies an additional edge-case patch. Its inherited parent tests therefore run against a different stacked source state and are a real composition regression, not an exact duplicate.

The caching parent-swap module's explicit optimized-child test also remains a locally declared test. This policy changes ordinary repository discovery only; it does not rewrite direct module behavior or the child matrix.

## Candidate contract

`tools/run_fieldwork_unittests.py`:

- performs ordinary `unittest` discovery from `tests/`;
- registers both the repository root and tests directory as import roots;
- retains existing unqualified sibling-test imports and `tools.*` package imports;
- flattens the discovered suite while preserving discovery order;
- removes an inherited method only when its exact fully qualified class is in the explicit policy and the method name is absent from that class's `__dict__`;
- retains locally declared overrides;
- retains all tests from every non-policy class;
- fails closed if a policy class is no longer discovered;
- reports discovered, retained, and removed counts;
- supports execution, list-only, and JSON summary modes;
- returns the underlying unittest success or failure status.

Repository CI invokes the runner as a module:

```text
python3 -m tools.run_fieldwork_unittests --verbosity 2
```

Module execution preserves the repository root as an import path. The runner also inserts the repository and tests roots explicitly before discovery.

## Focused regression

`tests/test_fieldwork_unittest_discovery.py` discovers the actual repository suite without executing it and proves:

- every policy class is present;
- each policy class originally contains more discovered methods than it declares locally;
- the filtered class contains exactly its locally declared `test_*` methods;
- the summary removal count equals the removed inherited methods;
- the intentional tarfilter composition class retains its inherited contract tests;
- every non-policy test ID remains present and ordered;
- a stale policy class causes an explicit `DiscoveryPolicyError`.

## Why a central runner

Adding `load_tests` to each extension module would change direct module loading and the caching optimized child as well as repository CI. It would also distribute one discovery policy across unrelated test files.

The central runner makes the repository-level evidence policy explicit, keeps direct module semantics unchanged, and records why each exception exists in one reviewable place.

## Complete-diff review

Review checked:

- class IDs match default discovery's unqualified module names;
- repository and sibling import roots coexist;
- locally overridden methods remain callable and retained;
- flattened ordering preserves class and module fixture transitions;
- non-policy tests are byte-for-byte the same test instances in the same order;
- missing policy classes fail before execution;
- list and JSON modes do not run tests;
- workflow help and compilation gates include the runner;
- PR #302's changed-patch validator remains intact.

No test body, candidate source, imported product source, external workflow, secret, live target, destructive action, or external interaction is changed.

## Evidence boundary

This changes repository discovery authority and reported counts. It does not claim that every retained test is behaviorally independent, that direct file execution is deduplicated, or that future subclasses should automatically be suppressed.

A new class enters the policy only after showing that its inherited tests use the same fixture and source state. A subclass that overrides candidate preparation or another material fixture remains a composition rerun.

## Disposition

`REPAIR` until exact-head stacked Linux Fieldwork CI passes and reports the removed count while all retained tests succeed.

After PR #302 lands, retarget or restack this unit onto `main`. A green clean current-main result should move it to `MERGE LOCALLY`.

## Authority

Internal Linux Fieldwork tooling only. No external contact is included or authorized.
