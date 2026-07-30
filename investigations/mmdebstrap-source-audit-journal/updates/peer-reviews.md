# Update — peer review outcomes

## PR #70 — chrootless target TMPDIR

- Reviewed head: `6ad9e2e513c75c06d5e1b21744e94cf0fdbced94`
- Verdict: `accept-with-notes`
- Product result: preserving `TMPDIR` in the sanitized chrootless dpkg environment is sound because `run_setup()` has already created `<target>/tmp`, set mode `01777`, and replaced the caller value with the target-derived path before either call site.
- Executed evidence: the apt-managed maintainer-script path, target placement, mode, cleanup, rerun, and fakeroot checks passed dedicated run `30536534715`.
- Evidence note: direct `run_essential()` coverage is static shared-helper inspection, not a second executed essential-package transaction.
- The red generic CI job was not promoted into product evidence; its unit tests passed and the failure was in the repository-wide optional-help tail.

## PR #45 — old GNU sparse type normalization

- Reviewed head: `afc10939ed4921db2a3c5a7f4aed9941c084ae3e`
- Verdict: `accept-with-notes`
- Product result: parsed old-GNU sparse type `S` must be normalized to a regular-file type before PAX sparse 1.0 output or dense fallback.
- Regression result: the fixture establishes `GNUTYPE_SPARSE`, keeps an unmodified negative control, and requires regular output type, valid listing/extraction, content equality, sparse allocation, compact archive size, and dense fallback cleanup.
- Exact-head CI: run `30533724256`, success.
- Evidence note: the added dialect boundary is the old-GNU form emitted by the runner's GNU tar version.

## Review discipline

Both reviews separated source behavior from carrier and generic-CI failures. No upstream contact was made.