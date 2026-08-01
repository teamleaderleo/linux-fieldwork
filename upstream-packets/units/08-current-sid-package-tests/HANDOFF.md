# Current handoff

Updated: `2026-08-01`  
Worker or variant: `primary composition`  
State: `ACTIVE`

## Exact current identities

| Item | Value |
| --- | --- |
| Linux Fieldwork branch | `upstream/unit-08-current-sid-package-tests` |
| Linux Fieldwork technical head before this handoff commit | `c98e5ab023a28b3d1000b1d429fdc59e4acc729d` |
| Linux Fieldwork final branch head | commit containing this `HANDOFF.md`; #397 checkpoint records the returned SHA |
| Upstream base repository/branch | `https://salsa.debian.org/debian/mmdebstrap.git`; intended `master`, executable base tag `debian/1.5.7-3` |
| Upstream base commit | `6fde999741f4fe1e7bf38079acf29432ef87a35e` |
| Candidate fork/branch | `NEEDS FORK`; packet patch series only |
| Candidate head | `PENDING EXECUTED SERIES GATE` |
| Patch or series | `upstream-packets/units/08-current-sid-package-tests/patches/series` |
| Complete-series gate | `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` |
| Gate introducing commit | `7782872ae2f731a27ed672df3a37b1d3b1581aa4` |
| Owning issue/PR | #397 unit 08; clean integration carrier PR #361 |
| Latest distinguishing package run | PR #361 workflow `30640356619` / 999; artifact `8798679560`; ZIP SHA-256 `50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244` |

## Current bounded claim

Four upstream package-test corrections have been extracted into an ordered series against exact Debian mmdebstrap revision `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e`. Historical current-sid integration proves the selected Deb822 handling, status-zero process-group signal spelling, hook-free producer/consumer order, and broad-phase fixture regeneration reached the next independent result.

The branch now contains an executable complete-series gate. Its source parses and compiles, while the gate itself still needs execution against a full Linux Fieldwork checkout. The direct `/usr/bin/mmdebstrap` hunk and the exact four-patch series therefore remain pending exact-head execution.

## Work completed in this continuation

- refreshed issue #397 and confirmed the existing unit-08 claim;
- read the remaining direct carrier issue bodies/comments for #119 and #153, including the final #153 closeout receipt;
- confirmed the canonical accepted scheduling source is PR #359 and the real sid successor evidence is PR #361 run 999;
- reviewed the existing unit packet, ordered patches, decisions, drafts, and previous handoff;
- added `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` at `7782872ae2f731a27ed672df3a37b1d3b1581aa4`;
- made the test apply all four patches twice to fresh copies of the five changed imported-source files;
- required exact series order, zero fuzz, zero offset, expected patched paths, Python compilation, shell parsing, deterministic candidate digests, and unchanged imported-source digests;
- compiled and AST-parsed the exact test source locally;
- recorded the test-source receipt in `TESTS.md` and updated the source map, README, and decision log;
- checked branch-triggered workflows: none exist because Linux Fieldwork CI runs on `pull_request` or `workflow_dispatch`;
- attempted to open a draft internal Linux Fieldwork PR solely to activate CI; the connector safety classifier blocked the mutation, and no speculative retry was made;
- made no Debian, Salsa, mmdebstrap, email, review, or other public contact.

## Changed paths in this continuation

- `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`
- `upstream-packets/units/08-current-sid-package-tests/README.md`
- `upstream-packets/units/08-current-sid-package-tests/SOURCE_MAP.md`
- `upstream-packets/units/08-current-sid-package-tests/TESTS.md`
- `upstream-packets/units/08-current-sid-package-tests/DECISIONS.md`
- `upstream-packets/units/08-current-sid-package-tests/HANDOFF.md`

The complete unit branch also retains:

- `DEEP_DIVE.md`;
- `UPSTREAM_ISSUE.md`;
- `UPSTREAM_PR.md`;
- four numbered patch files and `patches/series`.

## Exact new evidence

Test-source validation executed in a transient local file:

```text
py_compile=PASS
ast_parse=PASS
sha256=a16b060b02a7c9e1b43db600f0f5789e6e5fc3add7cf93dc95ca32ad314b3dd6
```

Interpretation:

- the committed test module is syntactically valid Python;
- the receipt does not prove patch application because this runtime lacked a materialized repository checkout;
- `/tmp/test_unit08.py` and `/tmp/__pycache__` were removed after the check.

Workflow/connector receipt:

```text
commit 7782872ae2f731a27ed672df3a37b1d3b1581aa4: workflow_runs=[]
draft internal PR creation: blocked by connector safety classifier
```

Interpretation:

- branch push alone cannot execute the repository gate under the current workflow triggers;
- the blocked mutation is an interaction/tool event, not package, patch, security, or compatibility evidence.

## Distinguishing observations

- Exploded Deb822 entries proxy their parent file path read-only; root raw file paths before calling `exploded_list()`.
- The historical installed-command proxy served reduction and changed source-preflight ownership. The upstream-facing correction is a direct stable installed path.
- Current sid accepted dash builtin `kill -s INT -- -PGID` with whole-group delivery and status 0; external long signal forms rejected the target.
- `root-without-cap-sys-admin` must run without mount-dependent hooks and retain hard failure semantics.
- `tar1.txt` belongs to an execution phase. The focused phase needs explicit producer `create-directory`; the broad phase must run the same producer again under broad hooks.
- Run 999 cleared the unit-08 phase behavior and first failed independently at `chrootless`, owned by #380.

## Gates completed

- predecessor Deb822 execution reached later package cases;
- PR #326 repository and dedicated sid signal gates passed on exact head;
- PR #359 focused scheduling/application gate passed 369 tests on its generated merge;
- PR #361 run 999 passed the focused pair and later broad producer in real sid execution;
- complete carrier/source ownership review finished for the selected four-patch boundary;
- complete-series gate source was committed, byte-compiled, and AST-parsed;
- branch contains no public upstream action and no LF-only source machinery in the candidate series.

## Gates still open

- execute `tests.test_upstream_packet_unit_08_current_sid_package_tests` against a full checkout;
- record both exact patch-application receipts and candidate digests;
- run focused upstream-native Deb822, command-path, SIGINT, focused-pair, and broad-regeneration tests on the distilled series;
- run current sid from the exact upstream-facing series without the LF proxy/evidence carrier;
- fetch current Salsa `master`, record its exact commit, search overlap, and reapply/rebase the series;
- review the final exact upstream diff after the live rebase;
- obtain explicit authorization before creating any Salsa fork or merge request.

## Red or neutral runs classified

- PR #72 early Deb822 assertion: package-test compatibility defect, repaired by patch 0001.
- PR #72 cwd-changing proxy loss: disposable carrier path defect, distilled to patch 0002.
- procps long-form signal rejection: current-sid command compatibility defect, repaired by patch 0003.
- capability-case mount failure: hook contradiction, repaired by patch 0004.
- run 939 missing `tar1.txt`: focused fixture prerequisite, repaired by explicit prefix.
- run 974 broad archive mismatch: phase-stale baseline, repaired by broad producer regeneration.
- run 999 `chrootless` directory mtimes: independent later source-policy result; routed to #380.
- blocked draft internal PR: connector safety event; package claim none.

## Cleanup state

No local package installation, mount, socket, container, long-running process, or source-tree mutation survives. The only local test artifact was `/tmp/test_unit08.py`; it and generated Python cache files were removed. Historical run 999's privileged container exited and artifact upload completed.

GitHub intentionally retains the unit branch, packet, patches, executable test, and internal issue coordination comments.

## First incomplete step

Execute the committed complete-series gate from a full checkout of this branch and retain its exact output.

## Next safe action

From a full checkout of `teamleaderleo/linux-fieldwork` on `upstream/unit-08-current-sid-package-tests`, run:

```sh
python3 -m unittest -v \
  tests.test_upstream_packet_unit_08_current_sid_package_tests
```

Expected behavior:

1. both fresh applications pass;
2. every receipt names only the expected patched files;
3. no receipt contains `fuzz` or `offset`;
4. transformed Python and shell files parse;
5. first and second candidate digests and receipts match;
6. imported source digests remain unchanged;
7. temporary directories are removed after each run.

Record complete stdout/stderr and the exact checkout commit in `TESTS.md`. Run the same command immediately again. After that, fetch current Salsa `master`, record its commit, perform overlap review, and rerun the gate against the refreshed source before any current-sid package execution.

A human may alternatively open a draft internal Linux Fieldwork PR for this branch or invoke `linux-fieldwork-ci.yml` manually. The connector blocked that mutation in this session, so the next worker should use the normal repository UI or an authorized local GitHub client instead of repeating the blocked connector call.

## Unresolved blockers

- technical: the committed complete-series gate has not executed against the repository tree;
- compatibility: direct `/usr/bin/mmdebstrap` selection has historical rationale and still needs exact-head execution;
- overlap: current Salsa `master` has yet to be fetched and searched for equivalent changes;
- environment/tooling: this runtime could read the connected repository but could not materialize it locally, branch pushes do not trigger CI, and draft-PR creation was blocked by the connector classifier;
- authority: Salsa fork/MR creation and every public upstream action require explicit authorization.

## Files to read first

1. `README.md`
2. `TESTS.md`
3. `SOURCE_MAP.md`
4. `DEEP_DIVE.md`
5. `DECISIONS.md`
6. `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`
7. issue #397 unit 08, PR #359, and PR #361

## External-contact state

`false; none occurred`. The only outward-looking text is stored as unpublished drafts in this packet. The #397 claim/checkpoint are internal Linux Fieldwork coordination.

## Do not repeat

- avoid reviving the relative formatted installed-command proxy as upstream source;
- avoid moving the capability consumer into the soft phase that maps ordinary failures to 77;
- avoid marking `create-directory` hook-free-only, which starves broad baseline regeneration;
- avoid rerunning the full sid matrix solely to reproduce run-999 `chrootless`; #380 owns the timestamp decision;
- avoid treating PR #72 as the live delivery carrier; PR #361 preserves clean integration evidence;
- avoid claiming current Salsa `master` from the package tag without a fresh fetch and overlap review;
- avoid retrying the blocked draft-PR connector mutation without a changed authorization/tooling path;
- avoid contacting Debian or mmdebstrap upstream without explicit authorization.
