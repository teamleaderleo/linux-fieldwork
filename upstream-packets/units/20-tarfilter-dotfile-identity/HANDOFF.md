# Handoff

## Unit and state

- Unit: 20 — mmdebstrap tarfilter dotfile identity
- State: `ACTIVE`
- Worker: GPT-5.6 Thinking
- Linux Fieldwork branch: `upstream/unit-20-tarfilter-dotfile-identity`
- Linux Fieldwork base: `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Internal draft PR: #408
- Last semantic technical head before this documentation batch: `7b92189ace1de4138d753830f8032c244f1276c6`
- External-contact state: unauthorized; internal work only

The final branch tip after this documentation batch is recorded in the unit checkpoint on issue #397. This handoff deliberately leaves the unit `ACTIVE`; the final exact-head workflow and artifact review remain incomplete.

## Exact upstream identities

- Repository: `josch/mmdebstrap`
- Base branch: `main`
- Main head observed 2026-08-01: `77ec9be5417ee44c96343d2347145585da1b1f94`
- `tarfilter` last-change commit: `87b9b385b38795c58bc13ffb33b8724bed27f7a0`
- Source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- `coverage.txt` blob: `87f4cccf5fc646c82600672113830419e20b95dd`
- `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- `run_null.sh` blob: `e0a8c106f9d3d636baea286d2ab33834748dffc9`
- Controlled upstream fork: `NEEDS FORK`
- Intended delivery: Forgejo fork and pull request

## Current candidate identities

- Patch: `patches/0001-tarfilter-preserve-dotfile-identity.patch`
- Patch Git blob: `fca86c0a45cb7f7c2e8534b4dacf8b2dafd55342`
- Locally computed patch SHA-256: `e9a71c6afe34f3170c27cc81a93006bf5d6eb2fe863fd7dd32e7f46c8719171b`
- Test: `tests/tarfilter-path-dotfiles`
- Test Git blob: `516f4e1f3a38175257b68a9d9e524495d7531564`
- Locally computed test SHA-256: `9fbc4c1146bdeb199713eb51279ce439e78ff96fc7be711f68b2278aa052e910`
- Workflow blob before documentation batch: `bf769608742c71e4f3bdd2a1c700905ac1d0c02a`

The workflow recomputes these hashes on the exact canonical checkout. Use the artifact hashes as final execution identities.

## Completed work

1. Read issue #397, packet README and index, repository start and field guides, cross-context notes, issue #38, duplicate issue #28, issues #29 and #39, PR #33, every combined patch, and every focused test carrier.
2. Claimed unit 20 and created `upstream/unit-20-tarfilter-dotfile-identity` from current Linux Fieldwork main.
3. Confirmed canonical mmdebstrap main and exact source/test-runner blobs.
4. Confirmed current upstream still uses `member.name.lstrip("./")`.
5. Split the dotfile source hunk from no-option, sparse, parent-retention, wildcard-parent, transform, PAX, and hard-link dependency work.
6. Built a focused three-file upstream patch.
7. Expanded the upstream-style test from a narrow name set to a 249-line matrix covering ordering, root aliases, ordinary and multi-dot names, parent components, repeated leading prefixes, file types, payload, metadata, and link targets.
8. Ran and retained a real dpkg 1.22.22 path-filter differential.
9. Ran and retained a GNU tar 1.35 consumer path matrix.
10. Added a mutation matrix making four attractive alternatives lose.
11. Found and repaired the first candidate's archive-root regression.
12. Found and repaired ambiguous test executable authority.
13. Found and repaired Git executable-mode loss in the patch gate.
14. Added an exact canonical-source workflow with identity checks, baseline loss, two fresh candidate generations, direct and registered execution, cleanup, rerun, differentials, hashes, and artifacts.
15. Added branch-scoped concurrency to cancel future superseded exact-head generations.
16. Opened internal draft PR #408 as the review and CI carrier.
17. Rewrote the packet with explicit known/unknowns, residual risk, stop conditions, and reopen triggers.

## Selected correction

```python
def normalize_filter_path(name):
    while name.startswith(("./", "/")):
        name = name[2:] if name.startswith("./") else name[1:]
    if name == ".":
        name = ""
    return "/" + name
```

The helper removes only complete leading archive syntax prefixes, preserves dots and leading `..` components, and keeps archive-root aliases matched as `/`.

## Distinguishing evidence

### Current source loses

- `.config` aliases `config`.
- `..name` and `...name` lose dots.
- `../config` aliases `/config`.

### First candidate loses

- `.`, `./.`, and `/.` map to `/.`, changing archive-root matching.

### Selected candidate wins the local discriminators

- complete leading-prefix mapping matrix;
- root aliases;
- real dpkg ordinary-package path identity;
- GNU tar leading-prefix consumer identity;
- regular, directory, symlink, and hard-link metadata controls;
- explicit executable authority;
- Git patch mode preservation design.

See `DEEP_DIVE.md`, `TESTS.md`, and `artifacts/`.

## Current exact-execution state

- Draft PR: #408
- Workflow: `Unit 20 tarfilter dotfile identity`
- Last run before documentation batch: `30691603829`
- Last observed state: queued
- That run targets semantic technical head `7b92189ace1de4138d753830f8032c244f1276c6`.
- The documentation batch creates a replacement exact head and workflow generation.

## First incomplete step

Fetch the newest workflow run for the final branch tip, then:

1. inspect job steps and logs;
2. classify the first result as source, candidate, test, runner, environment, cleanup, or evidence;
3. repair any failure and rerun from a fresh final head;
4. download the `unit-20-canonical-upstream-gate` artifact;
5. retain the run ID, job ID, artifact ID, hashes, candidate diff, baseline output, direct output, registered output, cleanup status, and rerun output in the packet;
6. perform the final active-overlap recheck and complete-diff review.

## Stop condition

Advance to `READY FOR AUTHORIZATION` only when one exact final head passes all of:

- canonical commit and blob verification;
- current expanded losing baseline;
- direct candidate test;
- registered `coverage.py` test;
- zero-fuzz dry-run and Git application;
- executable test-mode assertion;
- exact three-file upstream diff;
- syntax, shellcheck, and shfmt;
- cleanup and immediate rerun;
- dpkg, GNU tar, and mutation probes;
- artifact and hash retention;
- overlap recheck;
- residual internal-dot question recorded outside the patch.

## Residual and successor boundary

GNU tar treats `foo/./.config` as `foo/.config`. Unit 20 retains that as a successor question because whole-path normalization also affects `..` and exceeds the leading-prefix claim. Do not silently broaden the current patch.

Parent metadata retention remains unit 21. No-option passthrough remains unit 18.

## Cleanup state

Local disposable `.deb` roots, tar extraction directories, generated archives, and mutation outputs were removed after their receipts were retained. No process, mount, socket, lock, container, or generated archive remains intentionally active.

Hosted workflow cleanup must still be verified from the final artifact.

## Publication boundary

No upstream issue, pull request, comment, email, review, or other external contact has been created. Linux Fieldwork PR #408 and issue #397 comments are internal repository coordination. Explicit authorization remains required for upstream contact.
