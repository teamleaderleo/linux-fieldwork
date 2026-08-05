# vmspawn carrier status

- Controlled fork: `teamleaderleo/systemd`
- Test branch: `research/vmspawn-unmapped-bind-userns-1652be7`
- Test-only head: `a257ad03b07257f9b1eb47412a224a9da30db2e4`
- Exact snapshot base: `canonical/main-1652be7`
- Exact canonical base commit: `1652be7df88d358c1e215c7de5431505348e5ab3`
- Internal draft PR: `teamleaderleo/systemd#7`
- PR state at latest review: open, draft, mergeable
- PR scope: one TEST-87 ordinary-user vmspawn bind-startup discriminator
- Product source changes: none
- Local source-only receipt: exact script passes `bash -n`
- Hosted static receipt: Linux Fieldwork run `31012029092`, job `92326394818`, success
- Hosted static coverage: exact checkout identity, canonical-base ancestry, `git diff --check`, `bash -n`, ShellCheck with the repository helper path, and clean checkout all passed
- Runtime receipt: pending
- Submitted reviews/comments: none observed on controlled PR #7
- Expected baseline classification: test failure with `Failed to enter user namespace for virtiofsd: Operation not permitted`
- Passing candidate classification: vmspawn reaches QEMU and the external timeout returns 124
- External contact: none

The hosted static gate validates the exact repaired carrier, including the EXIT-trap ShellCheck annotation. It does not establish vmspawn runtime behavior. The next technical gate is execution of the ordinary-user TEST-87 case in a systemd test environment with QEMU, virtiofsd, a bootable kernel, and `testuser`. The blank-disk case remains a host-startup discriminator; guest-visible bind contents are still required before a product candidate is complete.
