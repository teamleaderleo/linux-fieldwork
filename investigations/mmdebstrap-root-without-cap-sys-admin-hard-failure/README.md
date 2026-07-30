# Hook-free capability tests must keep hard-failure semantics

## Finding

The Debian package test injects `sourcesfilter` and `file-mirror-automount` into its main host-APT phase. `root-without-cap-sys-admin` deliberately drops `CAP_SYS_ADMIN`, so the bind-mount hook fails before the case reaches its `/proc/self/fd` invariant.

Merged PR #158 proposed `Needs-APT-Config: true` so the case would move to the existing hook-free phase. Post-merge audit found that phase explicitly treats failures as irrelevant and runs:

```sh
coverage.py ... $SKIPPED_TESTS || exit 77
```

That removes the incompatible hook but weakens an authoritative coverage invariant into a neutral result. Issue #153 required the case not be silently skipped, so it was reopened.

## Corrected candidate

The retained patch introduces a separate metadata class:

```text
Needs-Hook-Free-APT-Config: true
```

The field is added to `coverage.py`'s explicit configuration whitelist; otherwise the parser would reject the new paragraph before any scheduling decision. The host-APT scheduler then skips either incompatible class while `USE_HOST_APT_CONFIG=yes`.

After the package test rebuilds its hook-free mirror, `debian/tests/testsuite` runs the new class separately with:

```text
CMD=mmdebstrap
```

and no injected hooks. Its status policy is:

- success 0 remains 0;
- ordinary failures such as 1 or 2 are propagated unchanged;
- timeout 124 remains neutral 77 as a time-budget outcome.

The original `Needs-APT-Config` transition list remains a distinct soft-failure phase.

## Regression

`tests/test_mmdebstrap_hook_free_hard_failure.py`:

- applies the patch to exact temporary copies of `coverage.txt`, `coverage.py`, and `debian/tests/testsuite`;
- proves the capability case uses only the new metadata;
- parses the candidate Python source and proves the new field is present in the config whitelist but absent from the baseline;
- proves the host-APT skip recognizes the new metadata;
- proves the hard phase precedes the soft phase and contains neither injected hook;
- extracts and executes the actual candidate status block, requiring 0→0, 1→1, 2→2, and 124→77;
- preserves the original capability drop, `/proc/self/fd`, and tar assertions;
- compiles the Python driver and checks package-test shell syntax.

`tests/test_mmdebstrap_hook_free_hard_failure_guards.py` executes the complete candidate hard-phase shell block and requires:

- an empty metadata class to fail with status 1 before `timeout` runs;
- exhausted remaining time to return 77 before `timeout` runs;
- a selected child status 2 to remain status 2.

## Push validation

Helper B reviewed the complete four-file diff and repaired the guard harness at commit `c38e15db62143e91a81df0ec72e7bfecce726569`: the per-run parent directory is now created before fake commands and the extracted shell block execute.

Exact GitHub Actions run `30577002902` then passed on Ubuntu 24.04:

```text
python3 -m unittest discover -s tests -v
Ran 98 tests in 21.445s
OK
```

The ten Packet B tests all passed, including parser acceptance, hook exclusion, 0/1/2/124 classification, empty selection, exhausted time, hard child failure, syntax, and unchanged capability assertions. Shell syntax and command-help gates also passed.

A focused reconstructed-source guard run was executed twice after the harness repair; all three guard tests passed both times and temporary directories were removed after each run.

The candidate differs from current `main` only by the four files in PR #171. The branch is one commit behind `main`; that commit changes only `ADAPTIVE_COORDINATION.md`, so it has no source or test overlap with this candidate. The pull-request merge ref built successfully against that current base.

## Evidence boundary

This is package-test scheduling and result classification only. It does not change mmdebstrap product behavior, the imported source tree, or historical Debian bug ownership.

The focused repository gates prove the retained patch and scheduling contract. PR #72 owns the disposable current-sid composition run that applies this exact patch alongside the Deb822 reduction candidate.

No external contact is included or authorized. Refs #153, merged #158, PR #171, and PR #72.
