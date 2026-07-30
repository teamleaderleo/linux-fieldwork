from __future__ import annotations

import mailbox
import sys
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import debian_bug_report  # noqa: E402


class DebianBugReportTest(unittest.TestCase):
    def test_summarizes_mbox_messages_and_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.mbox"
            box = mailbox.mbox(path)
            try:
                first = EmailMessage()
                first["From"] = "Reporter <reporter@example.test>"
                first["To"] = "submit@bugs.debian.org"
                first["Date"] = "Mon, 29 Jun 2026 12:59:01 +0000"
                first["Subject"] = "mmdebstrap autopkgtest fails"
                first["Message-Id"] = "<first@example.test>"
                first.set_content(
                    "See https://ci.debian.net/data/autopkgtest/testing/amd64/m/mmdebstrap/1/log.gz.\n"
                )
                box.add(first)

                second = EmailMessage()
                second["From"] = "Maintainer <maintainer@example.test>"
                second["To"] = "1141078@bugs.debian.org"
                second["Subject"] = "Re: mmdebstrap autopkgtest fails"
                second["Message-Id"] = "<second@example.test>"
                second.set_content("Reproduced with test example-test.\n")
                box.add(second)
                box.flush()
            finally:
                box.close()

            summary = debian_bug_report.summarize_mbox(
                path,
                1141078,
                debian_bug_report.report_url(1141078),
            )

        self.assertEqual(summary["message_count"], 2)
        self.assertEqual(
            summary["messages"][0]["subject"],
            "mmdebstrap autopkgtest fails",
        )
        self.assertEqual(
            summary["urls"],
            [
                "https://ci.debian.net/data/autopkgtest/testing/amd64/m/mmdebstrap/1/log.gz"
            ],
        )
        self.assertEqual(len(summary["mbox_sha256"]), 64)

    def test_markdown_summary_contains_provenance(self) -> None:
        summary = {
            "bug": 1141078,
            "source_url": debian_bug_report.report_url(1141078),
            "mbox_bytes": 123,
            "mbox_sha256": "a" * 64,
            "message_count": 1,
            "messages": [
                {
                    "index": 0,
                    "date": "date",
                    "from": "from",
                    "to": "to",
                    "subject": "subject",
                    "message_id": "id",
                    "plain_text_bytes": 4,
                    "plain_text_sha256": "b" * 64,
                    "urls": [],
                }
            ],
            "urls": [],
        }

        rendered = debian_bug_report.markdown_summary(summary)

        self.assertIn("Debian bug 1141078 capture", rendered)
        self.assertIn("`" + "a" * 64 + "`", rendered)
        self.assertIn("### Message 0", rendered)


if __name__ == "__main__":
    unittest.main()
