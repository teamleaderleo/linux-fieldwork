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

The carrier adds `.github/workflows/relative-exec-cwd-inventory.yml`.

It runs on pull requests that change any audited root and:

- checks out the proposed repository state without persisting credentials;
- runs the landed scanner across the exact audited roots;
- validates the complete typed JSON finding schema;
- writes the finding count and escaped identities to the job summary;
- uploads the raw JSON inventory for 14 days;
- remains read-only and Ubuntu-only.

The existing dedicated workflow retains scanner regressions, downloaded-receipt validation, and the Windows Rust identity probe. Those expensive or implementation-specific jobs remain tied to scanner-development changes.

## Review repairs

### Rendered summary text

Complete review found that paths, executable strings, and cwd expressions originate in pull-request-controlled source. Writing them directly inside a Markdown code fence would place unescaped untrusted text on a rendered job-summary surface.

The broad inventory workflow keeps raw typed values only in the artifact and HTML-escapes each rendered summary line inside `<pre>` markup. A focused contract test forbids the earlier raw Markdown-fence form.

### Checkout credential lifetime

The repository is public. Even so, proposed scanner and Rust fixture source runs after checkout, so retaining the checkout credential in Git configuration creates an unnecessary token surface.

Both the new broad inventory workflow and both checkout steps in the existing dedicated workflow set `persist-credentials: false`. Focused contract tests require those settings.

### Raw finding output in the dedicated audit

The dedicated Linux inventory previously printed every pull-request-controlled path, executable, and cwd value directly to the Actions log after schema validation. Actions logs interpret workflow-command syntax, so raw untrusted identity text does not belong on that channel.

The current dedicated workflow prints only the validated finding count. The raw typed identities remain in the uploaded JSON artifact and are revalidated by the receipt job.

## Decision boundary

Findings remain review prompts. The new workflow does not use `--fail-on-findings`, because the scanner is literal and heuristic and some reported launches can be intentional. The workflow fails when scanner execution or evidence-schema validation fails, not merely because findings exist.

A future policy may promote selected finding classes to hard failures only after the repository has an explicit suppression or ownership mechanism. That is outside this carrier.

## Exact carrier

```text
branch: ci/relative-exec-cwd-inventory-coverage
base: 6cc74d846c50b9bbb88247e8a128b67e8c174c1e
head before this record update: 8214d7f217e96ef288a7b2dd96a479177a9865ba
```

## Five-file fence

1. `.github/workflows/relative-exec-cwd-inventory.yml`;
2. `.github/workflows/relative-exec-cwd-audit.yml`;
3. `tests/test_relative_exec_cwd_inventory_workflow.py`;
4. `tests/test_relative_exec_cwd_audit_receipt.py`;
5. this record.

## Gates

Required before landing:

```sh
python3 -m unittest -v tests.test_relative_exec_cwd_inventory_workflow
python3 -m unittest -v \
  tests.test_relative_exec_cwd_audit \
  tests.test_relative_exec_cwd_audit_receipt \
  tests.test_relative_exec_cwd_inventory_workflow
```

The broad inventory, existing dedicated audit, and repository CI must all pass on the same exact head.

## Authority

Internal Linux Fieldwork tooling only. No OpenAI, Codex, Debian, RPFM, or other external contact is authorized or included.
