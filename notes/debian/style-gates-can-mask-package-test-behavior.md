# Style gates can mask package-test behavior

## In simple words

A package test can fail before it exercises the program behavior that prompted the investigation. Formatting, lint, generated-file, or policy checks may run first and stop the suite.

When the style tool in the test environment is newer than the tool used to build the installed package, reformatting the installed script may fail even though the package's runtime behavior has not been tested at all.

## What I learned

Keep these questions separate:

1. Does the source tree satisfy its chosen style policy?
2. Does the installed package behave correctly in the current system?

A test harness that uses one command path for both responsibilities can couple them accidentally. If a current formatter examines an older installed script before behavioral execution, the result is a style-compatibility finding, not evidence for or against the runtime defect.

A bounded diagnostic control can use a tiny source-tree wrapper that:

- is judged by the current style gate;
- uses `exec` so it does not add process or settlement behavior;
- forwards every argument unchanged;
- explicitly invokes the installed program for the actual test cases.

The override must be recorded, hashed, and described. It must not be presented as a production fix or silently removed from the evidence boundary.

## Source and provenance

- Project: Debian `mmdebstrap`
- Test: `debian/tests/testsuite` and `coverage.sh`
- Investigation: `investigations/mmdebstrap-autopkgtest-1141078/`
- Original contained run: `30514378292`
- Original first test-suite failure: `perltidy failed`

## Validation

The focused regression applies the wrapper patch to the exact imported testsuite and requires the behavioral command to execute `/usr/bin/mmdebstrap`. The full control runs the Debian sid autopkgtest in a disposable container and retains the first failure after the style gate.

Unsafe output roots are tested separately so diagnostic cleanup cannot erase arbitrary caller paths.

## Limits

This method does not decide the correct Debian style policy and must not be used to hide source formatting defects in normal CI. It is appropriate only when the bounded question is installed runtime behavior and the style check is demonstrably blocking that question for an independently versioned artifact.

## Related work

- Draft PR #9: broad historical investigation
- Focused current-main style-gate control carrier
- Debian bug #1141078 remains external and read-only
