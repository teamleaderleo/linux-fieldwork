from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


class LF02EvidenceProvenanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo = pathlib.Path(__file__).resolve().parents[1]
        module_path = repo / (
            "programmes/rootless-execution/lanes/"
            "LF-02-chrootless-dpkg-root-containment/scouts/"
            "LF-SCOUT-ROOT-01/artifacts/write-provenance.py"
        )
        spec = importlib.util.spec_from_file_location(
            "lf02_evidence_provenance", module_path
        )
        assert spec is not None and spec.loader is not None
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_actions_detached_head_retains_pull_request_refs(self) -> None:
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "teamleaderleo/linux-fieldwork",
            "GITHUB_EVENT_NAME": "pull_request",
            "GITHUB_WORKFLOW": "Verify LF-02 chrootless containment",
            "GITHUB_WORKFLOW_REF": (
                "teamleaderleo/linux-fieldwork/.github/workflows/"
                "lf-02-chrootless-dpkg-root-containment.yml@refs/pull/21/merge"
            ),
            "GITHUB_RUN_ID": "30515782245",
            "GITHUB_RUN_NUMBER": "9",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_JOB": "containment",
            "GITHUB_SHA": "merge-sha",
            "GITHUB_REF": "refs/pull/21/merge",
            "GITHUB_REF_NAME": "21/merge",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_HEAD_REF": "scout/lf-scout-root-01/lf-02-dpkg-root-containment",
            "GITHUB_BASE_REF": "main",
        }
        provenance = self.module.build_provenance(
            env=env,
            repo_root=pathlib.Path("/work/repo"),
            runtime=pathlib.Path("/runner/temp/lf02"),
            result_dir=pathlib.Path("/work/repo/artifacts/results"),
            git_head="checked-out-merge-sha",
            symbolic_branch=None,
        )

        repository = provenance["repository"]
        github = provenance["github_actions"]
        self.assertTrue(repository["detached_head"])
        self.assertIsNone(repository["symbolic_branch"])
        self.assertEqual(
            repository["effective_ref"],
            "scout/lf-scout-root-01/lf-02-dpkg-root-containment",
        )
        self.assertEqual(repository["checked_out_head"], "checked-out-merge-sha")
        self.assertTrue(github["active"])
        self.assertEqual(github["sha"], "merge-sha")
        self.assertEqual(github["ref"], "refs/pull/21/merge")
        self.assertEqual(github["head_ref"], repository["effective_ref"])
        self.assertEqual(github["base_ref"], "main")
        self.assertEqual(github["run_id"], "30515782245")
        self.assertIn(
            "repository_branch=<unset>",
            self.module.environment_lines(provenance),
        )
        self.assertIn(
            "repository_detached_head=true",
            self.module.environment_lines(provenance),
        )

    def test_local_branch_has_explicit_non_actions_provenance(self) -> None:
        provenance = self.module.build_provenance(
            env={},
            repo_root=pathlib.Path("/work/repo"),
            runtime=pathlib.Path("/tmp/lf02"),
            result_dir=pathlib.Path("/work/repo/results"),
            git_head="local-sha",
            symbolic_branch="topic/local",
        )
        self.assertFalse(provenance["github_actions"]["active"])
        self.assertFalse(provenance["repository"]["detached_head"])
        self.assertEqual(provenance["repository"]["effective_ref"], "topic/local")
        self.assertEqual(
            provenance["github_actions"]["run_id"],
            None,
        )
        lines = self.module.environment_lines(provenance)
        self.assertIn("github_actions=false", lines)
        self.assertIn("github_run_id=<unset>", lines)
        self.assertIn("repository_branch=topic/local", lines)

    def test_normalized_view_replaces_ephemeral_roots(self) -> None:
        repo = pathlib.Path("/home/runner/work/linux-fieldwork/linux-fieldwork")
        runtime = pathlib.Path("/home/runner/work/_temp/lf-02-run")
        result_dir = repo / "lane/artifacts/results"
        raw = (
            f"{runtime}/tool --repo={repo} --summary={result_dir}/summary.json\n"
        )
        normalized = self.module.normalize_text(
            raw,
            repo_root=repo,
            runtime=runtime,
            result_dir=result_dir,
        )
        self.assertEqual(
            normalized,
            "<runtime>/tool --repo=<repo-root> "
            "--summary=<result-dir>/summary.json\n",
        )
        self.assertNotIn("/home/runner", normalized)

    def test_empty_actions_values_are_null_not_ambiguous_empty_strings(self) -> None:
        provenance = self.module.build_provenance(
            env={
                "GITHUB_ACTIONS": "true",
                "GITHUB_HEAD_REF": "",
                "GITHUB_REF_NAME": "main",
                "GITHUB_REF": "refs/heads/main",
            },
            repo_root=pathlib.Path("/repo"),
            runtime=pathlib.Path("/tmp/run"),
            result_dir=pathlib.Path("/repo/results"),
            git_head="sha",
            symbolic_branch=None,
        )
        self.assertIsNone(provenance["github_actions"]["head_ref"])
        self.assertEqual(provenance["repository"]["effective_ref"], "main")


if __name__ == "__main__":
    unittest.main()
