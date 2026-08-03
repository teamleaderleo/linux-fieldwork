# vmspawn carrier status

- Controlled fork: `teamleaderleo/systemd`
- Test branch: `research/vmspawn-unmapped-bind-userns`
- Test-only head: `8a2d77b08f511d30a9cb81c9f2c147dfd5aa638b`
- Exact snapshot base: `linux-fieldwork/upstream-main-snapshot-2026-08-03`
- Exact canonical base commit: `ac33190d1f66e870d511827cbed3ebeee2d704c2`
- Internal draft PR: `teamleaderleo/systemd#6`
- PR state at latest review: open, draft, mergeable
- PR scope: one TEST-87 shell discriminator
- Product source changes: none
- Local source-only receipt: exact script passes `bash -n`
- Local shellcheck receipt: unavailable; shellcheck is not installed in the execution container
- Hosted static receipt: queued in Linux Fieldwork run `30802233175`, job `91649238382`
- Runtime receipt: pending
- Submitted reviews/comments: none observed
- Expected baseline classification: test failure with `Failed to enter user namespace for virtiofsd: Operation not permitted`
- Passing candidate classification: vmspawn reaches QEMU and the external timeout returns 124
- External contact: none

The Bash syntax result establishes only parser validity for the exact carrier script. The queued hosted job still owns ancestry, diff, shellcheck, and clean-checkout validation. The blank-disk test is a host-startup discriminator; guest-visible bind contents remain a required stronger gate before a product candidate is considered complete.
