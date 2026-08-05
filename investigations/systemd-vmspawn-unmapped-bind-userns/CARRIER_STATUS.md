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
- Prior hosted static receipt: Linux Fieldwork run `31012029092`, job `92326394818`, success on predecessor head `a257ad03b07257f9b1eb47412a224a9da30db2e4`
- Current-head hosted static receipt: pending after Fieldwork pin commit `24dac5a8f03b96be3dea7952ac2eb2b3ea691f3a`
- Runtime receipt: pending
- Submitted reviews/comments: none observed on controlled PR #7
- Expected baseline classification: test failure with `Failed to enter user namespace for virtiofsd: Operation not permitted`
- Passing candidate classification: vmspawn reaches QEMU and the external timeout returns 124
- External contact: none

Complete-diff review found that the predecessor cleanup unconditionally disabled linger and could change preexisting host state. The current carrier records and restores the initial linger and user-manager state. The next gate is exact-head static execution, followed by the ordinary-user TEST-87 runtime in an environment with QEMU, virtiofsd, a bootable kernel, and `testuser`. The blank-disk case remains a host-startup discriminator; guest-visible bind contents are still required before a product candidate is complete.
