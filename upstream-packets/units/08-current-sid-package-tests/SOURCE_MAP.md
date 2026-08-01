# Source map

## Canonical upstream source

- Repository: `https://salsa.debian.org/debian/mmdebstrap.git`
- Imported package revision: `debian/1.5.7-3`
- Resolved commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Import record: `upstream/mmdebstrap/.linux-fieldwork-source.json`
- Current sid source-package version observed during this pass: `1.5.7-3`

## Upstream files changed by the candidate

| File | Owner in this unit | Candidate behavior |
| --- | --- | --- |
| `debian/tests/sourcesfilter` | patch 0001 | Root raw source file paths before exploding Deb822 paragraphs; process exploded entries. |
| `debian/tests/testsuite` | patches 0002 and 0004 | Select the installed binary by absolute path; add the hook-free hard phase and phase-local producer. |
| `tests/sigint-during-customize-hook` | patch 0003 | Deliver SIGINT to the negative process-group ID through the status-zero dash builtin spelling. |
| `coverage.txt` | patch 0004 | Mark only `root-without-cap-sys-admin` as the hook-free hard consumer. |
| `coverage.py` | patch 0004 | Accept the metadata and skip the class while host APT hooks are active. |

## Upstream tests and fixtures involved

| Test or fixture | Relationship |
| --- | --- |
| `tests/create-directory` | Writes `tar1.txt`; exact prerequisite for the focused capability consumer and ordinary producer for broad consumers. |
| `tests/root-without-cap-sys-admin` | Drops `CAP_SYS_ADMIN`, runs mmdebstrap, verifies `/proc/self/fd`, and diffs archive listing against `tar1.txt`. |
| `tests/unshare-as-root-user` | Broad consumer that exposed stale hook-free `tar1.txt` through hook-specific APT paths. |
| `tests/cwd-directory-not-accessible-by-unshared-user` | Exposed the carrier's relative installed-command proxy after `env --chdir`; motivates the distilled absolute installed path. |
| `tests/sigint-during-customize-hook` | Exercises whole-group interruption and child result handling. |
| `debian/tests/testsuite` | Owns all four corrections' package execution order and environment. |

## Carrier map

| Carrier | Unique evidence retained | Delivery status |
| --- | --- | --- |
| #119 | Deb822 assertion mechanism and raw-file/exploded-entry ordering. | Source patch retained as 0001. |
| PR #72 | Historical disposable composition, real sid first failures, absolute proxy path, and package artifacts. | Evidence only; proxy/workflow removed. |
| #153 | Hard-failure classification for the hook-free capability case. | Policy carried through 0004. |
| PR #171 | Metadata scheduler, selector and timeout edge analysis, focused status matrix. | Superseded source; policy provenance. |
| #320 | procps parser rejection under current sid. | Evidence for 0003. |
| PR #326 | Whole-group topology plus status-zero candidate selection on sid. | Probe machinery excluded; selected spelling retained. |
| #350 | `create-directory` identified as exact `tar1.txt` producer. | Producer prerequisite carried in 0004. |
| #357 | Broad-phase stale baseline diagnosis. | Phase-local regeneration carried in 0004. |
| PR #354 | Fixture-complete focused pair and exact application controls. | Superseded by PR #359. |
| PR #359 | Accepted consumer-only metadata plus focused producer prefix and broad producer regeneration. | Exact merged patch is the source for 0004. |
| PR #361 | Clean current-main sid run 999: focused pair and later broad producer passed; next failure at `chrootless`. | Execution evidence only. |

## Candidate patch files

- `patches/0001-tests-sourcesfilter-accept-deb822.patch`
- `patches/0002-tests-use-absolute-installed-mmdebstrap.patch`
- `patches/0003-tests-use-current-sid-process-group-sigint.patch`
- `patches/0004-tests-run-capability-case-in-phase-local-hook-free-pass.patch`
- `patches/series`

## Linux Fieldwork execution gate

- `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`
- committed at `7782872ae2f731a27ed672df3a37b1d3b1581aa4`;
- copies the five changed imported-source files into a temporary tree;
- applies the exact ordered series twice with `patch --fuzz=0`;
- rejects any fuzz or offset receipt and checks every expected patched path;
- compiles transformed Python, parses transformed shell, compares deterministic candidate digests, and verifies the imported source bytes remain unchanged.

## Explicitly excluded local files

- `.github/workflows/*` related to disposable sid reproduction or signal probing;
- `investigations/mmdebstrap-autopkgtest-1141078/installed-command-wrapper.patch` as a complete patch;
- `scripts/capture-linux-context.sh` and `scripts/reproduce-mmdebstrap-autopkgtest.sh`;
- `tools/debian_bug_report.py`, `tools/reorder_mmdebstrap_hook_free_phase.py`, and `tools/probe_process_group_kill.py`;
- all LF-only `tests/test_mmdebstrap_*`, process-group probe tests, checkout classifiers, artifact receipts, and hosted-run metadata.

## Ownership and overlap boundary

- Unit 08 owns package-test compatibility and scheduling through the first independent result.
- Issue #380 owns the later `chrootless` directory-mtime policy.
- Unit 09 owns the separate `bsdutils` dependency for `dev-ptmx`.
- Unit 10 owns exact subordinate-ID matching.
- Unit 11 owns generic `coverage.py` backend cancellation.
