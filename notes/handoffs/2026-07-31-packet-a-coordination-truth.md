# Packet A: submission record and coordination truth

Packet: A  
Helper: Helper A  
Review date: 2026-07-31 (+08:00)  
Repository main reviewed: `d344c942af4b55b5b0c71c8a66a8870fbf0db7bf`  
Canonical handoff carrier before this update: PR #187 at `4a8e71538d420dc2303d7eff7e7d0d4e0cb5433d`

## In simple words

The patch for Debian bug #1135727 was sent successfully through Outlook and accepted into the existing Debian bug thread. Debian's tracker added the `patch` tag. This record replaces the earlier prepared-only authority text and names the live internal coordination surfaces and current candidate heads.

## Debian bug #1135727 submission

### Actual sent message

- Sent through: Outlook Sent Items
- Sender: `Leo Li <cheerleaderleo@outlook.com>`
- To: `1135727@bugs.debian.org`
- Cc: `1135727-submitter@bugs.debian.org`
- Subject: `[PATCH] mmdebstrap: honor non-empty TMPDIR as an exact parent directory`
- Sent time: `2026-07-30 16:34:37 UTC` / `2026-07-31 00:34:37 +08:00`
- Control pseudo-header: `Control: tags -1 + patch`
- Attachment name: `0001-honor-explicit-tmpdir-current.patch`
- Attachment media type reported by Outlook: `text/x-diff`
- Attachment size reported by Outlook: `3915` bytes

The actual Cc was the Debian submitter alias. It differed from the prepared draft, which named the reporter's direct address.

### Debbugs receipts

- `2026-07-30 16:37:06 UTC` / `2026-07-31 00:37:06 +08:00`: Debian Bug Tracking System sent `Bug#1135727: Info received`, confirming receipt and forwarding to the package maintainer at `josch@debian.org`.
- `2026-07-30 16:37:08 UTC` / `2026-07-31 00:37:08 +08:00`: the control command added the `patch` tag to bug #1135727.
- A second processing receipt at the same second ignored the repeated tag request because the same tag was already set.

These receipts establish message delivery into the existing bug and successful control-command processing. They do not establish maintainer review, patch acceptance, package upload, bug closure, or full-suite validation.

## Canonical handoff decision

PR #187 is the canonical durable handoff carrier. Its two original notes retain the work-period history; this Packet A record carries the later submission fact and current routing truth. PR #186 was already closed without merge after its unique material was transferred. No second handoff carrier is needed.

Disposition for PR #187: `MERGE LOCALLY` after the exact branch diff and repository-focused checks pass. After merge, the live queue and desk remain issues #189 and #190, while issue #194 owns the parallel push receipts.

## Live coordination surfaces

- Issue #189: human judgment queue.
- Issue #190: delivery, landing, and closeout desk.
- Issue #194: active parallel push and receipt contract.
- PR #187: canonical historical handoff to land locally.
- Issue #193: QEMU signal plus atomic-image integration owner.

Live pull-request heads reviewed for the queue refresh:

| Unit | Exact head | Current routing fact |
|---|---|---|
| PR #192 | `f6d438e978f03c52de48a9c3465de0d825b809bd` | Atomic QEMU publication candidate is review-ready; compose with PR #172 under issue #193. |
| PR #172 | `99129032602f0bfcf3dc2c7a24a8e96916aa9722` | Focused QEMU signal-exit mechanism; integration evidence remains separate. |
| PR #171 | `c38e15db62143e91a81df0ec72e7bfecce726569` | Hook-free hard-failure correction changed since the queue snapshot; exact-head receipt owns its disposition. |
| PR #161 | `58f5554860485be9a1b242dc3c23aa5f2255f4a1` | Read-only classifier/note candidate is review-ready with recorded green CI. |
| PR #151 | `beb4ff0c33722f78123da4d3c33d016bd7e9e83d` | GNU tar regex candidate changed since the queue snapshot. |
| PR #177 | `fbf63489916da81c851bee4b0ef1a474275bd014` | `--status-fd` parser candidate changed since the queue snapshot. |
| PR #180 | `a7c453a28e531faa883e63f943a773667023b2bb` | Verifier signal candidate changed since the queue snapshot. |
| PR #147 | `9029378cd4ebe069b13c72c2a07352b98ab3c48b` | Post-commit proxy error candidate changed since the desk snapshot. |
| PR #178 | `40c2b1ec89e4d8391bbcbe95a14f96a4a87760ca` | LF-02 lifecycle matrix remains draft pending hosted execution. |
| PR #109 | `f4c9fce1b0377f1fb61e3d13188c7294c3e1c692` | Chrootless PATH candidate remains a held draft pending exact-head gates. |

Unchanged queue heads still require their packet-specific receipts: PR #118 `190ce2263cf0c1aeab6d472df0e4f1c08946848d`, PR #162 `2c85a106f5bda256a0a1f7090c0bf6b95df386fe`, PR #169 `3ae3a6501653f273af25adae0279d072795e5a2f`, PR #179 `25cc47fc70abcb9a8693c831ce2e9ee7826a4d65`, PR #138 `9b71d143e958e2b2b0823785cbfaf22839d31850`, PR #143 `b0b87f9f1b30816b21dddcb6c3657b5a75b2b7f9`, PR #159 `6231f49963129ea1a75d8f4db6cca3a8e5b63a68`, and PR #166 `f57b43b32d78ad5dcd58039c816907fe7abe27de`.

Changed heads expire the older head text in #189, #190, and the original PR #187 snapshots. Live PR metadata and packet receipts remain authoritative.

## Composition and overlap

- The workspace-TMPDIR patch sent on bug #1135727 concerns mmdebstrap's own temporary root selection. It is separate from the target-derived maintainer-script `TMPDIR` correction in merged PR #74.
- PR #192 and PR #172 touch the same QEMU helper/trap region. Issue #193 owns their composed source state; neither focused result proves the integrated lifecycle.
- PR #187 carries coordination evidence only. It must not absorb code candidates or substitute for their exact-head gates.

## Evidence and test boundary

The submission facts were checked against Outlook Sent Items, attachment metadata, and the three Debbugs receipt messages. The repository check verifies exact recipient, attachment, receipt, tag, routing, and authority text. It does not fetch the public bug log, compare the sent attachment byte-for-byte with the retained repository patch, execute the complete 283-case source matrix, or run Debian autopkgtest.

## External-contact state

The already-sent patch on Debian bug #1135727 is the sole current external-contact exception recorded by issue #194. Replies on that same public bug may preserve the thread. Every other Debian, Ubuntu, GNU, Python, Linux, or other upstream issue, email, patch, merge request, comment, or review still requires a deliberate decision.

## Next human decision

Merge the corrected PR #187 documentation to `main`, then treat #189, #190, #194, and each exact-head packet receipt as the live routing sources. No additional external message is needed for Packet A.