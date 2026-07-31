from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import audit_pr_carrier_state as audit


class CarrierStateAuditTest(unittest.TestCase):
    def pr(
        self,
        number: int,
        body: str,
        *,
        title: str = "Example",
        state: str = "OPEN",
    ) -> dict[str, object]:
        return {
            "number": number,
            "title": title,
            "body": body,
            "url": f"https://github.com/example/repo/pull/{number}",
            "state": state,
        }

    def test_narrative_terminal_words_do_not_opt_in(self) -> None:
        body = """## Superseded history

The stopped predecessor remains useful evidence. This active PR continues.
"""
        self.assertEqual(audit.audit([self.pr(10, body)]), [])

    def test_fenced_field_examples_do_not_opt_in(self) -> None:
        examples = [
            """```text
Carrier state: active | component-evidence | superseded | stopped
Successor: #NUMBER | none
```""",
            """~~~
Carrier state: stopped
Successor: none
~~~""",
            """````markdown
```
Carrier state: superseded
Successor: #99
```
````""",
        ]
        for index, body in enumerate(examples, start=70):
            with self.subTest(body=body):
                self.assertEqual(audit.audit([self.pr(index, body)]), [])

    def test_real_fields_survive_beside_fenced_examples(self) -> None:
        body = """```text
Carrier state: active | component-evidence | superseded | stopped
Successor: #NUMBER | none
```

Carrier state: active
Successor: none
"""
        self.assertEqual(audit.audit([self.pr(75, body)]), [])

    def test_active_and_component_evidence_are_passing_controls(self) -> None:
        items = [
            self.pr(11, "Carrier state: active\nSuccessor: none\n"),
            self.pr(
                12,
                "Carrier state: component-evidence\nSuccessor: #19\n",
            ),
        ]
        self.assertEqual(audit.audit(items), [])

    def test_superseded_open_carrier_is_flagged(self) -> None:
        findings = audit.audit(
            [self.pr(13, "Carrier state: superseded\nSuccessor: #21\n")]
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "terminal-carrier-open")
        self.assertEqual(findings[0].carrier_state, "superseded")
        self.assertEqual(findings[0].successor, "#21")

    def test_stopped_open_carrier_is_flagged(self) -> None:
        findings = audit.audit(
            [self.pr(14, "Carrier state: stopped\nSuccessor: none\n")]
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "terminal-carrier-open")
        self.assertEqual(findings[0].carrier_state, "stopped")

    def test_duplicate_or_partial_fields_fail_closed(self) -> None:
        cases = [
            "Carrier state: active\nCarrier state: stopped\nSuccessor: none\n",
            "Carrier state: active\n",
            "Successor: #20\n",
        ]
        for index, body in enumerate(cases, start=20):
            with self.subTest(body=body):
                findings = audit.audit([self.pr(index, body)])
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0].kind, "malformed-declaration")

    def test_state_successor_relationships_are_exact(self) -> None:
        cases = [
            (30, "Carrier state: active\nSuccessor: #31\n"),
            (31, "Carrier state: component-evidence\nSuccessor: none\n"),
            (32, "Carrier state: superseded\nSuccessor: none\n"),
            (33, "Carrier state: stopped\nSuccessor: #34\n"),
            (34, "Carrier state: unknown\nSuccessor: none\n"),
            (35, "Carrier state: component-evidence\nSuccessor: 36\n"),
            (36, "Carrier state: component-evidence\nSuccessor: #36\n"),
        ]
        for number, body in cases:
            with self.subTest(body=body):
                findings = audit.audit([self.pr(number, body)])
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0].kind, "malformed-declaration")

    def test_closed_terminal_carrier_is_outside_open_inventory(self) -> None:
        item = self.pr(
            40,
            "Carrier state: stopped\nSuccessor: none\n",
            state="CLOSED",
        )
        self.assertEqual(audit.audit([item]), [])

    def test_exact_types_and_document_shape_fail_closed(self) -> None:
        bool_number = self.pr(50, "Carrier state: active\nSuccessor: none\n")
        bool_number["number"] = True
        findings = audit.audit([bool_number])
        self.assertEqual(findings[0].kind, "malformed-declaration")

        document_findings = audit.audit({"number": 50})
        self.assertEqual(document_findings[0].number, 0)
        self.assertEqual(document_findings[0].kind, "malformed-declaration")

    def test_cli_json_and_optimizer_status_match_findings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "tools" / "audit_pr_carrier_state.py"
        document = [
            self.pr(60, "Carrier state: active\nSuccessor: none\n"),
            self.pr(61, "Carrier state: stopped\nSuccessor: none\n"),
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            input_path = Path(tempdir) / "prs.json"
            input_path.write_text(json.dumps(document), encoding="utf-8")
            completed_runs = []
            for optimize in (False, True):
                command = [sys.executable]
                if optimize:
                    command.append("-O")
                command.extend([str(script), "--json", str(input_path)])
                completed_runs.append(
                    subprocess.run(
                        command,
                        cwd=root,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                )

        ordinary, optimized = completed_runs
        self.assertEqual(ordinary.returncode, 1, ordinary.stderr)
        self.assertEqual(optimized.returncode, 1, optimized.stderr)
        self.assertEqual(json.loads(ordinary.stdout), json.loads(optimized.stdout))
        payload = json.loads(ordinary.stdout)
        self.assertEqual([item["number"] for item in payload], [61])
        self.assertEqual(payload[0]["kind"], "terminal-carrier-open")


if __name__ == "__main__":
    unittest.main()
