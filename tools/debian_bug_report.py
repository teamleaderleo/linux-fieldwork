#!/usr/bin/env python3
"""Fetch and summarize a Debian BTS report as a retained mbox artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import mailbox
import re
import sys
import tempfile
import urllib.error
import urllib.request
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path
from typing import Any, Iterable

MAX_REPORT_BYTES = 32 * 1024 * 1024
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+")


def report_url(bug: int) -> str:
    return f"https://bugs.debian.org/cgi-bin/bugreport.cgi?bug={bug};mbox=yes"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decoded_header(message: Message, name: str) -> str:
    raw = message.get(name, "")
    try:
        return str(make_header(decode_header(raw)))
    except (LookupError, UnicodeError):
        return raw


def plain_text_parts(message: Message) -> Iterable[str]:
    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.get_content_type() != "text/plain":
            continue
        disposition = part.get_content_disposition()
        if disposition == "attachment":
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            raw = part.get_payload()
            if isinstance(raw, str):
                yield raw
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            yield payload.decode(charset, errors="replace")
        except LookupError:
            yield payload.decode("utf-8", errors="replace")


def clean_url(url: str) -> str:
    return url.rstrip(".,;:!?)]}")


def summarize_mbox(path: Path, bug: int, source_url: str) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    all_urls: set[str] = set()

    box = mailbox.mbox(path, create=False)
    try:
        for index, message in enumerate(box):
            text = "\n".join(plain_text_parts(message))
            urls = sorted({clean_url(item) for item in URL_RE.findall(text)})
            all_urls.update(urls)
            messages.append(
                {
                    "index": index,
                    "message_id": decoded_header(message, "Message-Id"),
                    "date": decoded_header(message, "Date"),
                    "from": decoded_header(message, "From"),
                    "to": decoded_header(message, "To"),
                    "subject": decoded_header(message, "Subject"),
                    "plain_text_bytes": len(text.encode("utf-8")),
                    "plain_text_sha256": sha256_bytes(text.encode("utf-8")),
                    "urls": urls,
                }
            )
    finally:
        box.close()

    if not messages:
        raise ValueError("downloaded report contains no mbox messages")

    report_bytes = path.read_bytes()
    return {
        "bug": bug,
        "source_url": source_url,
        "mbox_bytes": len(report_bytes),
        "mbox_sha256": sha256_bytes(report_bytes),
        "message_count": len(messages),
        "messages": messages,
        "urls": sorted(all_urls),
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"# Debian bug {summary['bug']} capture",
        "",
        f"- Source: `{summary['source_url']}`",
        f"- Mbox bytes: `{summary['mbox_bytes']}`",
        f"- Mbox SHA-256: `{summary['mbox_sha256']}`",
        f"- Messages: `{summary['message_count']}`",
        "",
        "## Messages",
        "",
    ]
    for item in summary["messages"]:
        lines.extend(
            [
                f"### Message {item['index']}",
                "",
                f"- Date: `{item['date']}`",
                f"- From: `{item['from']}`",
                f"- To: `{item['to']}`",
                f"- Subject: `{item['subject']}`",
                f"- Message-ID: `{item['message_id']}`",
                f"- Plain-text bytes: `{item['plain_text_bytes']}`",
                f"- Plain-text SHA-256: `{item['plain_text_sha256']}`",
                "",
            ]
        )
        if item["urls"]:
            lines.append("Referenced URLs:")
            lines.append("")
            lines.extend(f"- `{url}`" for url in item["urls"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def fetch_report(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "linux-fieldwork-debian-bug-capture/1",
            "Accept": "application/mbox,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_REPORT_BYTES:
            raise ValueError(f"report exceeds {MAX_REPORT_BYTES} bytes")
        data = response.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError(f"report exceeds {MAX_REPORT_BYTES} bytes")
    return data


def write_capture(output_dir: Path, bug: int, data: bytes, url: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mbox_path = output_dir / f"bug-{bug}.mbox"
    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    temporary_path.replace(mbox_path)

    summary = summarize_mbox(mbox_path, bug, url)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        markdown_summary(summary),
        encoding="utf-8",
    )
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bug", type=int)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory for the mbox and summaries",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.bug <= 0:
        print("debian_bug_report: bug number must be positive", file=sys.stderr)
        return 2
    url = report_url(args.bug)
    try:
        data = fetch_report(url, args.timeout)
        summary = write_capture(args.output_dir, args.bug, data, url)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"debian_bug_report: {exc}", file=sys.stderr)
        return 1
    print(
        f"captured bug {args.bug}: {summary['message_count']} messages, "
        f"sha256={summary['mbox_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
