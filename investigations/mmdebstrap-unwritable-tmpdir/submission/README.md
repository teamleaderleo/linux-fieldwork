# Debian bug #1135727 submission record

## Result

The patch follow-up was sent successfully through Outlook to the existing Debian bug on 2026-07-30 UTC. Debbugs acknowledged the message, forwarded it to the package maintainer, and added the `patch` tag.

## Actual sent envelope

- From: `Leo Li <cheerleaderleo@outlook.com>`
- To: `1135727@bugs.debian.org`
- Cc: `1135727-submitter@bugs.debian.org`
- Subject: `[PATCH] mmdebstrap: honor non-empty TMPDIR as an exact parent directory`
- Sent: `2026-07-30 16:34:37 UTC` / `2026-07-31 00:34:37 +08:00`
- Body record: `email.txt`
- Control pseudo-header: `Control: tags -1 + patch`

The actual Cc used Debian's submitter alias. The earlier prepared draft named the reporter's direct address; that planned envelope is superseded by this sent record.

## Attachment

- Actual sent filename: `0001-honor-explicit-tmpdir-current.patch`
- Outlook media type: `text/x-diff`
- Outlook size: `3915` bytes
- Canonical retained repository patch: `0001-honor-explicit-tmpdir.patch`

The mailbox metadata establishes the sent attachment's name, type, and size. This record does not claim a post-send byte-for-byte comparison between the mailbox attachment and the retained repository patch.

## Debbugs acknowledgement

Debian Bug Tracking System receipts recorded:

1. `2026-07-30 16:37:06 UTC` — `Bug#1135727: Info received`; the message was received and forwarded to `josch@debian.org`.
2. `2026-07-30 16:37:08 UTC` — `tags -1 + patch` added the `patch` tag to bug #1135727.
3. `2026-07-30 16:37:08 UTC` — a repeated processing receipt ignored the same tag request because the tag was already set.

The receipts prove delivery into the existing bug and successful tag processing. They do not prove maintainer review, patch acceptance, package upload, or bug closure.

## Verification boundary

The submitted message records focused Ubuntu 24.04 verification for unset, empty, writable, unwritable, missing, and non-directory `TMPDIR` values, plus Perl syntax, Perl::Critic severity 4, POD rendering, source line length, ShellCheck, and shfmt checks. The complete 283-case source matrix and Debian autopkgtest were not run.

Run the repository consistency check with:

```sh
python3 investigations/mmdebstrap-unwritable-tmpdir/submission/verify_submission_record.py
```

## Follow-up boundary

Any reply about this submitted patch should use `1135727@bugs.debian.org` so it remains in the public bug thread. Issue #194 records this already-open thread as the sole current external-contact exception. Every other upstream issue, email, patch, merge request, comment, or review requires a deliberate decision.

## Authority state

External contact occurred only through the sent follow-up on Debian bug #1135727 and its automated Debbugs processing. No other Debian or external upstream contact is included or authorized by this record.