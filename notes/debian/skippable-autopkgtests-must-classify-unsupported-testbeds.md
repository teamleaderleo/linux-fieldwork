# Skippable autopkgtests must classify unsupported testbeds explicitly

## In simple words

A package test can be valid only on a particular distribution, backend, architecture, or privilege environment. When the test declares itself `skippable`, an unsupported testbed should produce the test framework's neutral result rather than a generic failure.

A generic failure says the package behavior was tested and broke. A neutral result says the required test environment was absent or outside the declared support boundary.

## Stable lesson

Separate three outcomes:

- **supported environment, invariant passed** — exit `0`;
- **supported environment, invariant failed** — nonzero failure;
- **unsupported or unavailable required environment** — the framework's declared neutral/skip status.

For Debian autopkgtest, a test with the `skippable` restriction may return `77` to report a neutral result.

## Why early classification matters

Distribution and testbed checks often run before fixtures, mirrors, or behavioral cases. A hard exit from this stage can be misread as a product regression and combined with unrelated failures from another distribution.

The diagnostic should name the unsupported input, such as archive identity, architecture, backend, missing kernel feature, or privilege boundary. It should not silently continue with an arbitrary fallback.

## Shell boundary

When suite selection is performed inside command substitution under `set -e`, the assignment command receives the substitution's exit status. Returning `77` from the selector therefore stops the shell with `77` before later test work begins.

This boundary deserves an executable regression because shell error handling is easy to change accidentally.

## mmdebstrap example

The imported `mmdebstrap 1.5.7-3` package test accepts only Debian APT archive identities `stable`, `testing`, and `unstable`. It is marked `skippable`, but the selector currently exits `1` when none of those identities exists.

The Linux Fieldwork candidate in issue #55 changes only that unsupported-environment exit to `77`. Tests preserve Debian priority and trust selection, prove the old hard failure, require the new neutral status, and verify `/bin/sh` with `set -e` does not continue.

## Limits

A neutral skip is appropriate only when the test deliberately does not support the environment. It must not hide a failure in an environment the test claims to support. Adding real cross-distribution support requires separate mirrors, suite identities, package expectations, and regression coverage.

## Related records

- Issue #55
- `investigations/mmdebstrap-autopkgtest-nondebian-skip/README.md`
- Debian bug triage coordination: #53
