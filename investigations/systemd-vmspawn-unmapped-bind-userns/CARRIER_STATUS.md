# vmspawn carrier status

- Controlled fork: `teamleaderleo/systemd`
- Test branch: `research/vmspawn-unmapped-bind-userns-1652be7`
- Test-only head: `741db5faed175180d427526b3878d5527d838b2d`
- Exact snapshot base: `canonical/main-1652be7`
- Exact canonical base commit: `1652be7df88d358c1e215c7de5431505348e5ab3`
- Internal draft PR: `teamleaderleo/systemd#7`
- PR state at latest review: open, draft, mergeable
- PR scope: one TEST-87 ordinary-user vmspawn bind-startup discriminator
- Product source changes: none
- Carrier cleanup: preserves preexisting `testuser` linger and `user@UID.service` activity, while removing only state introduced by the test
- Hosted static receipt: Linux Fieldwork run `31012029092`, job `92326394818`, success with the exact test head pinned
- First hosted runtime: Linux Fieldwork run `31103506350`, job `92622705684`, harness-owned failure before vmspawn execution
- First runtime result: `testuser` could not traverse the runner workspace; `timeout` returned `126` with `Permission denied`
- First runtime cleanup result: test-owned temporary state was removed, but the workflow's broad `pkill -f` pattern could match its own cleanup shell
- Runtime repair: stage the exact binary and matching `libsystemd-shared-262.so` under an ordinary-user-traversable `/tmp` root; verify the staged binary as `testuser`; use self-safe bracketed process-match patterns; remove only workflow-owned user and staging state
- Repaired hosted runtime: Linux Fieldwork run `31104102608`, job `92624711637`, queued and not yet a result
- Submitted reviews/comments: none observed on controlled PR #7
- Expected source baseline classification: test failure with `Failed to enter user namespace for virtiofsd: Operation not permitted`
- Passing candidate classification: vmspawn reaches QEMU and the external timeout returns `124`
- External contact: none

Complete-diff review found that the predecessor cleanup unconditionally disabled linger and could change preexisting host state. The current carrier records and restores the initial linger and user-manager state.

The first hosted runtime demonstrated only a test-harness accessibility failure: the exact built binary was inside the runner workspace, which the dropped ordinary user could not traverse. It did not classify current vmspawn source behavior. The repaired workflow copies the exact binary and its matching shared library into a disposable `/tmp` tree, checks dependency resolution, executes `systemd-vmspawn --version` as `testuser`, and then runs the same TEST-87 discriminator with that staged binary.

The blank-disk case remains a host-startup discriminator. Guest-visible bind contents are still required before a product candidate is complete. No source candidate should be materialized until the repaired baseline reaches and classifies the current source path.
