#!/usr/bin/env python3
"""Capture portable LF-02 evidence provenance and normalize path-bearing views."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any

GITHUB_FIELDS = (
    "GITHUB_REPOSITORY",
    "GITHUB_EVENT_NAME",
    "GITHUB_WORKFLOW",
    "GITHUB_WORKFLOW_REF",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_NUMBER",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_JOB",
    "GITHUB_SHA",
    "GITHUB_REF",
    "GITHUB_REF_NAME",
    "GITHUB_REF_TYPE",
    "GITHUB_HEAD_REF",
    "GITHUB_BASE_REF",
)


def present(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


def build_provenance(
    *,
    env: Mapping[str, str],
    repo_root: pathlib.Path,
    runtime: pathlib.Path,
    result_dir: pathlib.Path,
    git_head: str,
    symbolic_branch: str | None,
) -> dict[str, Any]:
    """Build a stable record without assuming that HEAD names a branch."""

    branch = present(symbolic_branch)
    github = {name.removeprefix("GITHUB_").lower(): present(env.get(name)) for name in GITHUB_FIELDS}
    actions_active = env.get("GITHUB_ACTIONS") == "true"
    effective_ref = (
        github["head_ref"]
        or github["ref_name"]
        or github["ref"]
        or branch
    )

    return {
        "schema_version": 1,
        "repository": {
            "slug": github["repository"],
            "checked_out_head": git_head,
            "symbolic_branch": branch,
            "detached_head": branch is None,
            "effective_ref": effective_ref,
        },
        "github_actions": {
            "active": actions_active,
            "event_name": github["event_name"],
            "workflow": github["workflow"],
            "workflow_ref": github["workflow_ref"],
            "run_id": github["run_id"],
            "run_number": github["run_number"],
            "run_attempt": github["run_attempt"],
            "job": github["job"],
            "sha": github["sha"],
            "ref": github["ref"],
            "ref_name": github["ref_name"],
            "ref_type": github["ref_type"],
            "head_ref": github["head_ref"],
            "base_ref": github["base_ref"],
        },
        "path_views": {
            "raw": {
                "repository_root": str(repo_root),
                "runtime_root": str(runtime),
                "result_directory": str(result_dir),
            },
            "normalized_tokens": {
                "repository_root": "<repo-root>",
                "runtime_root": "<runtime>",
                "result_directory": "<result-dir>",
            },
        },
    }


def environment_lines(provenance: Mapping[str, Any]) -> list[str]:
    repository = provenance["repository"]
    github = provenance["github_actions"]

    def text(value: Any) -> str:
        if value is None:
            return "<unset>"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    return [
        f"provenance_schema_version={provenance['schema_version']}",
        f"repository_head={text(repository['checked_out_head'])}",
        f"repository_branch={text(repository['symbolic_branch'])}",
        f"repository_detached_head={text(repository['detached_head'])}",
        f"repository_effective_ref={text(repository['effective_ref'])}",
        f"github_actions={text(github['active'])}",
        f"github_repository={text(repository['slug'])}",
        f"github_event_name={text(github['event_name'])}",
        f"github_workflow={text(github['workflow'])}",
        f"github_workflow_ref={text(github['workflow_ref'])}",
        f"github_run_id={text(github['run_id'])}",
        f"github_run_number={text(github['run_number'])}",
        f"github_run_attempt={text(github['run_attempt'])}",
        f"github_job={text(github['job'])}",
        f"github_sha={text(github['sha'])}",
        f"github_ref={text(github['ref'])}",
        f"github_ref_name={text(github['ref_name'])}",
        f"github_ref_type={text(github['ref_type'])}",
        f"github_head_ref={text(github['head_ref'])}",
        f"github_base_ref={text(github['base_ref'])}",
    ]


def normalized_replacements(
    repo_root: pathlib.Path,
    runtime: pathlib.Path,
    result_dir: pathlib.Path,
) -> Sequence[tuple[str, str]]:
    candidates = (
        (str(result_dir), "<result-dir>"),
        (str(runtime), "<runtime>"),
        (str(repo_root), "<repo-root>"),
    )
    return tuple(sorted(candidates, key=lambda item: len(item[0]), reverse=True))


def normalize_text(
    text: str,
    *,
    repo_root: pathlib.Path,
    runtime: pathlib.Path,
    result_dir: pathlib.Path,
) -> str:
    for raw, token in normalized_replacements(repo_root, runtime, result_dir):
        text = text.replace(raw, token)
    return text


def git_value(repo_root: pathlib.Path, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return present(completed.stdout.strip())


def capture(args: argparse.Namespace) -> int:
    repo_root = pathlib.Path(args.repo_root).resolve()
    runtime = pathlib.Path(args.runtime).resolve()
    result_dir = pathlib.Path(args.result_dir).resolve()
    git_head = git_value(repo_root, "rev-parse", "HEAD")
    if git_head is None:
        raise SystemExit("unable to resolve repository HEAD")
    symbolic_branch = git_value(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    provenance = build_provenance(
        env=os.environ,
        repo_root=repo_root,
        runtime=runtime,
        result_dir=result_dir,
        git_head=git_head,
        symbolic_branch=symbolic_branch,
    )
    pathlib.Path(args.json_output).write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    pathlib.Path(args.env_output).write_text(
        "\n".join(environment_lines(provenance)) + "\n", encoding="utf-8"
    )
    return 0


def normalize(args: argparse.Namespace) -> int:
    input_path = pathlib.Path(args.input)
    output_path = pathlib.Path(args.output)
    output_path.write_text(
        normalize_text(
            input_path.read_text(encoding="utf-8", errors="replace"),
            repo_root=pathlib.Path(args.repo_root).resolve(),
            runtime=pathlib.Path(args.runtime).resolve(),
            result_dir=pathlib.Path(args.result_dir).resolve(),
        ),
        encoding="utf-8",
    )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--repo-root", required=True)
    capture_parser.add_argument("--runtime", required=True)
    capture_parser.add_argument("--result-dir", required=True)
    capture_parser.add_argument("--json-output", required=True)
    capture_parser.add_argument("--env-output", required=True)
    capture_parser.set_defaults(handler=capture)

    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("--repo-root", required=True)
    normalize_parser.add_argument("--runtime", required=True)
    normalize_parser.add_argument("--result-dir", required=True)
    normalize_parser.add_argument("--input", required=True)
    normalize_parser.add_argument("--output", required=True)
    normalize_parser.set_defaults(handler=normalize)
    return result


def main() -> int:
    args = parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
