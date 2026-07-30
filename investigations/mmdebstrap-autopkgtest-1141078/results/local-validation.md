# Local validation and execution boundary

## In simple words

The investigation tools received offline review and focused execution. The Debian package reproduction needs network access and a disposable root environment, both beyond the active local runtime.

## Observed local results

On 2026-07-30, focused checks established:

- both shell probes parse successfully;
- Linux context capture completes and marks host and sensitive fields as redacted by default;
- archive members with absolute paths or parent traversal are rejected;
- symlink targets retain their exact archive spelling;
- member order is observable through `archive_index`;
- timestamp-only drift can be separated from content and metadata drift;
- missing JSON fields remain distinct from fields whose value is `null`;
- synthetic Debian mbox messages parse into stable metadata, URL, size, and digest summaries.

## Self-review corrections

Earlier candidates contained several defects caught before merge:

1. Archive path normalization could hide an unsafe absolute or parent-traversal member. The tool now rejects such member paths.
2. Link-target normalization could change valid relative symlink semantics. Link targets are now preserved exactly.
3. Sorting the JSONL output could hide archive member-order differences. Each entry now records its original index.
4. Manifest comparison conflated a missing field with JSON `null`. Presence is now explicit.
5. Context capture exposed hostname, account names, subordinate-ID files, and full mount information. Public-safe output is now the default; sensitive capture requires an explicit flag.
6. Probe executable modes and repository placement were corrected during review.
7. Top-level guide replacements were removed after newer programme and target conventions landed on `main`.

## Unexecuted work

The active local container cannot resolve external hosts, including GitHub and Debian mirrors. Package installation and mirror preparation therefore cannot run there.

Several repository writes and an owner command were used to test GitHub Actions entry paths. Events created through the connected GitHub tool produced no Actions run records. The permanent workflow was returned to ordinary pull-request and manual-dispatch triggers, without PR-number-specific policy.

## Claim boundary

These results support the local tools and investigation method. They provide no result for Debian bug `#1141078` itself. The first complete package run remains required.
