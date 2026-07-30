#!/usr/bin/env python3
"""Find child launches whose relative executable path is coupled to a child cwd.

The findings are review prompts. A relative program can be intentional when it is
meant to live below the child cwd. The risky cases are commands whose author
resolved the program from one directory and later changed the child's cwd.
"""

from __future__ import annotations

import argparse
import ast
import json
import ntpath
import os
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


PYTHON_CALLS = {"run", "Popen", "call", "check_call", "check_output"}
RUST_COMMAND = re.compile(
    r'(?:std::process::|tokio::process::)?Command::new\(\s*"([^"]+)"\s*,?\s*\)'
)
SUPPORTED_SUFFIXES = {".py", ".rs", ".sh", ".bash"}
ENV_OPTIONS_WITH_VALUE = {"-a", "--argv0", "-u", "--unset"}
ENV_SHORT_OPTIONS_WITH_ATTACHED_VALUE = ("-a", "-u")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    language: str
    kind: str
    program: str
    cwd: str
    explanation: str


def is_relative_program_with_separator(program: str) -> bool:
    """Return true for a cross-platform relative program containing a separator."""

    if not program or os.path.isabs(program) or ntpath.isabs(program):
        return False
    return "/" in program or "\\" in program


def string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def keyword_value(call: ast.Call, name: str) -> ast.AST | None:
    return next((kw.value for kw in call.keywords if kw.arg == name), None)


def python_program(call: ast.Call) -> str | None:
    executable = keyword_value(call, "executable")
    if executable is not None:
        if isinstance(executable, ast.Constant) and executable.value is None:
            pass
        else:
            # A literal override is the executable identity. A dynamic override
            # makes that identity unknown, so do not report the decoy argv[0].
            return string_literal(executable)

    shell = keyword_value(call, "shell")
    if shell is not None:
        if isinstance(shell, ast.Constant) and shell.value in (False, None):
            pass
        else:
            # With shell=True, the command string is input to the shell rather
            # than the selected executable. Dynamic shell selection is also not
            # a high-confidence literal identity.
            return None

    if call.args:
        command = call.args[0]
    else:
        command = keyword_value(call, "args")
        if command is None:
            return None

    if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
        return string_literal(command.elts[0])
    return string_literal(command)


def python_call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def source_segment(source: str, node: ast.AST, fallback: str) -> str:
    segment = ast.get_source_segment(source, node)
    return segment.strip() if segment else fallback


def audit_python(path: str, source: str) -> list[Finding]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if python_call_name(node) not in PYTHON_CALLS:
            continue
        cwd_node = keyword_value(node, "cwd")
        if cwd_node is None:
            continue
        program = python_program(node)
        if program is None or not is_relative_program_with_separator(program):
            continue
        findings.append(
            Finding(
                path=path,
                line=node.lineno,
                language="python",
                kind="relative-program-with-cwd",
                program=program,
                cwd=source_segment(source, cwd_node, "<dynamic cwd>"),
                explanation=(
                    "The child changes cwd while the selected executable contains a relative path. "
                    "Confirm that the program is intentionally resolved inside the child cwd; "
                    "otherwise canonicalize it before launch."
                ),
            )
        )
    return findings


def rust_statement(lines: Sequence[str], start: int, limit: int = 50) -> str:
    collected: list[str] = []
    depth = 0
    for line in lines[start : start + limit]:
        collected.append(line)
        depth += line.count("(") + line.count("{") + line.count("[")
        depth -= line.count(")") + line.count("}") + line.count("]")
        if ";" in line and depth <= 0:
            break
    return "".join(collected)


def audit_rust(path: str, source: str) -> list[Finding]:
    lines = source.splitlines(keepends=True)
    findings: list[Finding] = []
    for match in RUST_COMMAND.finditer(source):
        program = match.group(1)
        if not is_relative_program_with_separator(program):
            continue
        line_number = source.count("\n", 0, match.start()) + 1
        statement = rust_statement(lines, line_number - 1)
        cwd_match = re.search(r"\.current_dir\((.*?)\)", statement, re.DOTALL)
        if cwd_match is None:
            continue
        findings.append(
            Finding(
                path=path,
                line=line_number,
                language="rust",
                kind="relative-program-with-current-dir",
                program=program,
                cwd=" ".join(cwd_match.group(1).split()),
                explanation=(
                    "Rust documents relative program resolution combined with current_dir as "
                    "platform-specific. Canonicalize the executable first or use a simple name "
                    "whose PATH lookup is the intended contract."
                ),
            )
        )
    return findings


def shell_logical_lines(source: str) -> Iterator[tuple[int, str]]:
    start_line = 1
    parts: list[str] = []
    for line_number, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.rstrip()
        if not parts:
            start_line = line_number
        if stripped.endswith("\\"):
            parts.append(stripped[:-1])
            continue
        parts.append(stripped)
        yield start_line, " ".join(parts)
        parts = []
    if parts:
        yield start_line, " ".join(parts)


def env_token_index(tokens: Sequence[str]) -> int | None:
    for index, token in enumerate(tokens):
        if token == "env" or token.endswith("/env"):
            return index
    return None


def is_environment_assignment(token: str) -> bool:
    return re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token) is not None


def is_split_string_option(token: str) -> bool:
    return token in {"-S", "--split-string"} or token.startswith(
        ("-S", "--split-string=")
    )


def shell_program_after_env(tokens: Sequence[str]) -> tuple[str, str] | None:
    env_index = env_token_index(tokens)
    if env_index is None:
        return None

    saw_chdir = False
    cwd = "<dynamic cwd>"
    options_ended = False
    index = env_index + 1
    while index < len(tokens):
        token = tokens[index]
        if not options_ended and token == "--":
            options_ended = True
            index += 1
            continue
        if not options_ended and token in {"--chdir", "-C"}:
            if index + 1 >= len(tokens):
                return None
            saw_chdir = True
            cwd = tokens[index + 1]
            index += 2
            continue
        if not options_ended and token.startswith("--chdir="):
            saw_chdir = True
            cwd = token.split("=", 1)[1]
            index += 1
            continue
        if not options_ended and token.startswith("-C") and token != "-C":
            saw_chdir = True
            cwd = token[2:]
            index += 1
            continue
        if not options_ended and is_split_string_option(token):
            # -S/--split-string creates a second command-parsing layer inside
            # one argument. This literal token scanner deliberately does not
            # guess the executable identity inside that string.
            return None
        if not options_ended and token in ENV_OPTIONS_WITH_VALUE:
            if index + 1 >= len(tokens):
                return None
            index += 2
            continue
        if not options_ended and any(
            token.startswith(prefix) and token != prefix
            for prefix in ENV_SHORT_OPTIONS_WITH_ATTACHED_VALUE
        ):
            index += 1
            continue
        if not options_ended and token.startswith("-"):
            index += 1
            continue
        if is_environment_assignment(token):
            index += 1
            continue
        break

    if not saw_chdir or index >= len(tokens):
        return None
    return tokens[index], cwd


def audit_shell(path: str, source: str) -> list[Finding]:
    findings: list[Finding] = []
    for line, logical in shell_logical_lines(source):
        try:
            tokens = shlex.split(logical, comments=True, posix=True)
        except ValueError:
            continue
        parsed = shell_program_after_env(tokens)
        if parsed is None:
            continue
        program, cwd = parsed
        if not is_relative_program_with_separator(program):
            continue
        findings.append(
            Finding(
                path=path,
                line=line,
                language="shell",
                kind="relative-program-after-env-chdir",
                program=program,
                cwd=cwd,
                explanation=(
                    "env changes directory before resolving this relative program. "
                    "Use a stable executable path when the program lives outside the new cwd."
                ),
            )
        )
    return findings


def language_for(path: Path, source: str) -> str | None:
    if path.suffix == ".py":
        return "python"
    if path.suffix == ".rs":
        return "rust"
    if path.suffix in {".sh", ".bash"}:
        return "shell"
    if source.startswith("#!") and any(
        name in source.splitlines()[0] for name in ("sh", "bash", "dash", "ksh")
    ):
        return "shell"
    return None


def audit_text(path: str, source: str, language: str | None = None) -> list[Finding]:
    selected = language or language_for(Path(path), source)
    if selected == "python":
        return audit_python(path, source)
    if selected == "rust":
        return audit_rust(path, source)
    if selected == "shell":
        return audit_shell(path, source)
    return []


def iter_files(paths: Iterable[Path]) -> Iterator[Path]:
    seen: set[Path] = set()
    for path in paths:
        if path.is_file():
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield path
            continue
        if not path.is_dir():
            continue
        for candidate in sorted(path.rglob("*")):
            if not candidate.is_file():
                continue
            if candidate.suffix not in SUPPORTED_SUFFIXES:
                try:
                    first = candidate.open(encoding="utf-8", errors="ignore").readline()
                except OSError:
                    continue
                if not first.startswith("#!"):
                    continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


def audit_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(paths):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(audit_text(str(path), source))
    return sorted(findings, key=lambda item: (item.path, item.line, item.kind))


def format_text(findings: Sequence[Finding]) -> str:
    if not findings:
        return "no relative executable / child cwd findings\n"
    return "".join(
        f"{item.path}:{item.line}: {item.kind}: program={item.program!r} "
        f"cwd={item.cwd!r}\n  {item.explanation}\n"
        for item in findings
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    findings = audit_paths(args.paths)
    if args.as_json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        print(format_text(findings), end="")
    return 1 if findings and args.fail_on_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
