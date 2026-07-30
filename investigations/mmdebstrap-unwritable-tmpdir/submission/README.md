# Debian bug #1135727 submission packet

## What to send

Send one plain-text email with:

- To: `1135727@bugs.debian.org`
- Cc: `mh+debian-packages@zugschlus.de`
- Subject: `[PATCH] mmdebstrap: honor non-empty TMPDIR as an exact parent directory`
- Body: `email.txt`, replacing `[Your name]`
- Attachment: `0001-honor-explicit-tmpdir.patch` as plain text or `text/x-patch`

The `Control: tags -1 + patch` pseudo-header in the body asks the Debian Bug Tracking System to add the `patch` tag to the existing report.

## Why these recipients

Mail to `1135727@bugs.debian.org` is recorded in the existing bug and forwarded to the package maintainer and Debian bug list. That address does not automatically send the follow-up to the original reporter, so the reporter is included in Cc.

Do not send this to `submit@bugs.debian.org`; that address is for creating a new report. Do not close the bug. Debian considers a package bug fixed after a corrected package enters the archive.

## Before sending

1. Configure the mail as plain text rather than HTML-only.
2. Replace `[Your name]` in `email.txt`.
3. Attach the patch without pasting repository notes or GitHub workflows.
4. Confirm that the attachment is not renamed or converted by the mail client.
5. Keep the acknowledgement from the Debian Bug Tracking System.

## After sending

Check the bug log for the message and the `patch` tag. The maintainer may apply the patch, request changes, ask for broader test results, or prefer a different implementation. Respond through the bug address so the discussion remains in the public record.

## Authority state

This packet is prepared locally. It has not been sent to Debian, the maintainer, or the reporter.
