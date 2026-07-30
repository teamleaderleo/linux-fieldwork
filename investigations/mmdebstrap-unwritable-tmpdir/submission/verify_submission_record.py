#!/usr/bin/env python3
"""Check the durable Debian bug #1135727 submission record."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INVESTIGATION = REPO_ROOT / "investigations/mmdebstrap-unwritable-tmpdir/README.md"
SUBMISSION = REPO_ROOT / "investigations/mmdebstrap-unwritable-tmpdir/submission/README.md"
EMAIL = REPO_ROOT / "investigations/mmdebstrap-unwritable-tmpdir/submission/email.txt"
HANDOFF = REPO_ROOT / "notes/handoffs/2026-07-31-packet-a-coordination-truth.md"


def require(text: str, *needles: str) -> None:
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"missing required text: {needle!r}")


def forbid(text: str, *needles: str) -> None:
    for needle in needles:
        if needle in text:
            raise AssertionError(f"stale text remains: {needle!r}")


def main() -> None:
    investigation = INVESTIGATION.read_text(encoding="utf-8")
    submission = SUBMISSION.read_text(encoding="utf-8")
    email = EMAIL.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    combined = "\n".join((investigation, submission, email, handoff))

    require(
        combined,
        "1135727@bugs.debian.org",
        "1135727-submitter@bugs.debian.org",
        "0001-honor-explicit-tmpdir-current.patch",
        "2026-07-30 16:34:37 UTC",
        "2026-07-30 16:37:06 UTC",
        "2026-07-30 16:37:08 UTC",
        "Control: tags -1 + patch",
        "added the `patch` tag",
        "ignored the repeated request",
        "josch@debian.org",
    )
    require(
        email,
        "To: 1135727@bugs.debian.org\n",
        "Cc: 1135727-submitter@bugs.debian.org\n",
        "Leo (Meng Hsi) Li",
    )
    require(
        handoff,
        "PR #187 is the canonical durable handoff carrier",
        "PR #192",
        "Issue #193",
        "PR #161",
        "c38e15db62143e91a81df0ec72e7bfecce726569",
    )
    forbid(
        combined,
        "This packet is prepared locally. It has not been sent",
        "No Debian issue, email, merge request, patch submission, comment, or review has been created",
        "Cc: mh+debian-packages@zugschlus.de",
        "[Your name]",
    )

    print("Debian bug #1135727 submission record: ok")


if __name__ == "__main__":
    main()
