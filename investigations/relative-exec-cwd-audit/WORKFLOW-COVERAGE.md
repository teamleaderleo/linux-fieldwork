# Relative executable audit workflow coverage

Date: 2026-08-03

## Finding

The landed scanner inventories these repository roots:

```text
tools tests scripts investigations programmes upstream
```

The dedicated workflow `.github/workflows/relative-exec-cwd-audit.yml` runs automatically only when the scanner, its focused tests, its fixtures, its investigation record, or that workflow changes.

Therefore, a pull request can add a new relative-executable/child-cwd pattern under one of the audited roots without automatically running the inventory. The scanner exists on `main`, but its automatic coverage is coupled to scanner maintenance rather than to the source trees it reviews.

## Repair

The focused carrier adds `.github/workflows/relative-exec-cwd-inventory.yml`.

It runs on pull requests that change any audited root and:

- checks out the proposed repository state;
- runs the landed scanner across the exact audited roots;
- validates the complete typed JSON finding schema;
- writes the finding count and identities to the job summary;
- uploads the JSON inventory for 14 days;
- remains read-only and Ubuntu-only.

The existing dedicated workflow retains scanner regressions, downloaded-receipt validation, and the Windows Rust identity probe. Those expensive or implementation-specific jobs remain tied to scanner-development changes.

## Decision boundary

Findings remain review prompts. The new workflow does not use `--fail-on-findings`, because the scanner is literal and heuristic and some reported launches can be intentional. The workflow fails when scanner execution or evidence-schema validation fails, not merely because findings exist.

A future policy may promote selected finding classes to hard failures only after the repository has an explicit suppression or ownership mechanism. That is outside this carrier.

## Exact carrier

```text
branch: ci/relative-exec-cwd-inventory-coverage
base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
workflow: .github/workflows/relative-exec-cwd-inventory.yml
contract test: tests/test_relative_exec_cwd_inventory_workflow.py
```

## Gates

Required before landing:

```sh
python3 -m unittest -v tests.test_relative_exec_cwd_inventory_workflow
python3 -m unittest -v \
  tests.test_relative_exec_cwd_audit \
  tests.test_relative_exec_cwd_audit_receipt \
  tests.test_relative_exec_cwd_inventory_workflow
```

The pull-request workflow must also execute on its own branch because both the new workflow and its test are included in the trigger paths.

## Authority

Internal Linux Fieldwork tooling only. No OpenAI, Codex, Debian, RPFM, or other external contact is authorized or included.
