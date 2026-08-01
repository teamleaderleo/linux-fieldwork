# Decision log

## 2026-08-01 — select PR #224 as the canonical top-level candidate

**Decision:** Use the exact patch at PR #224 head `13b3c529e983b3ad967725f99f4e31d867fa4742` as unit 13's canonical source correction. Treat PRs #159 and #205 as predecessor evidence.

**Reason:** #224 retains the parent termination, cleanup, reaping, rerun, and publication repair from #159/#205 and adds the missing ownership across both proxy launch-to-PID registration intervals. Its final revision also repairs first-signal handoff and first-launch cache-ownership test fidelity.

**Evidence:** `SOURCE_MAP.md`, `DEEP_DIVE.md`, PR #224 CI `30586490855`, complete review `4823717630`.

**Alternatives considered:**

- use #159/#205 unchanged;
- reopen the entire lifecycle from the original issue;
- create a new implementation despite an accepted exact patch.

**Consequences:**

- the packet retains one canonical patch;
- #159/#205 remain essential history and negative-control evidence;
- fresh current-source application and rerun become the next gate.

**Reopen trigger:** #224 patch fails zero-fuzz application, a fresh focused test fails, or complete current-upstream review finds a new top-level ownership defect.

**Authority effect:** Internal source work remains authorized. External contact remains unauthorized.

---

## 2026-08-01 — split top-level owner lifecycle from `update_cache()` worker lifecycle

**Decision:** Keep PRs #305/#324 outside the unit 13 product patch and route them to unit 14.

**Reason:** `update_cache()` runs in a pipeline subshell, owns its APT root, and returns a pipeline result. Unit 13 owns the parent shell, proxy PIDs, private-cache state, QEMU temporary state, and publication. The two lanes share one source file yet have separate process owners, invariants, test barriers, and result precedence.

**Evidence:** `SOURCE_MAP.md` ownership map; PR #324 patch targets the nested finalizer near line 156, while the unit 13 patch targets top-level lifecycle near the proxy launches.

**Alternatives considered:**

- one combined `make_mirror.sh` patch series;
- one broad issue with two commits;
- treat #305/#324 only as historical notes.

**Consequences:**

- unit 13 remains a single top-level patch;
- unit 14 carries worker-owned APT cleanup and cleanup-time signal precedence;
- each contribution can be reviewed and tested against one process owner.

**Reopen trigger:** upstream maintainers request one combined series, or fresh source drift makes the two patches inseparable.

**Authority effect:** No change to external-contact authority.

---

## 2026-08-01 — retain one source patch, with tests and explanation as review evidence

**Decision:** Prepare one upstream source commit for `make_mirror.sh`. Keep the two focused regression modules and packet records as evidence until the upstream test destination is decided.

**Reason:** All source edits implement one top-level owner invariant and overlap the same launch, trap, stop, and cleanup state. Splitting helper introduction from call-site conversion would create intermediate states with partial ownership.

**Evidence:** `DEEP_DIVE.md` “Why the changes belong together”; final #224 combined matrix.

**Alternatives considered:**

- separate signal-exit and launch-window commits;
- source-only patch with no retained focused tests;
- copy Linux Fieldwork tests directly into upstream before destination review.

**Consequences:**

- proposed patch order contains one source commit;
- test integration remains an explicit current-upstream decision;
- no half-repaired source commit becomes a delivery candidate.

**Reopen trigger:** upstream contribution guidance identifies a stable focused-test location or requests split commits.

**Authority effect:** Internal drafting remains authorized; no submission permission is implied.

---

## 2026-08-01 — classify current public source as byte-identical to the imported base

**Decision:** Treat public `make_mirror.sh` blob `6c4be092edcf23b56b63a3befe238c099c45f590` as the exact current source base for the next patch application gate.

**Reason:** The public Forgejo repository at `main` head `77ec9be5417ee44c96343d2347145585da1b1f94`, Debian dgit, and Linux Fieldwork imported source report the same file blob.

**Evidence:** `SOURCE_MAP.md`; public lookup dated 2026-08-01; PR #205 imported-blob receipt.

**Alternatives considered:**

- assume the retained patch is stale because its internal carrier predates the packet;
- use package version labels instead of exact source identity;
- declare rebase complete from blob identity alone.

**Consequences:**

- historical patch context is current at the byte level;
- fresh zero-fuzz application and execution remain required;
- no speculative source rewrite is justified.

**Reopen trigger:** upstream source blob changes or a fresh patch application produces any offset, fuzz, or conflict.

**Authority effect:** Public read-only verification occurred; no upstream contact occurred.

---

## 2026-08-01 — keep disposition ACTIVE after environment-blocked rerun

**Decision:** Leave unit 13 `ACTIVE`.

**Reason:** Carrier selection, source identity, scope, drafts, and patch packaging are complete. A fresh clone, zero-fuzz application, shell syntax check, focused rerun, and complete controlled-fork diff remain incomplete. The local runner failed DNS resolution before repository retrieval, so this pass produced no fresh executable candidate result.

**Evidence:** `TESTS.md` failure classification and unexecuted-gate list.

**Alternatives considered:**

- mark `READY FOR AUTHORIZATION` from historical CI alone;
- mark `HOLD` on DNS;
- create an upstream fork before explicit authorization.

**Consequences:**

- next work begins with one exact reproducible checkout/apply/test command;
- historical exact-head CI remains valid evidence without being presented as a fresh current-branch run;
- no external action occurs.

**Reopen trigger:** successful fresh execution can advance the unit toward `READY FOR AUTHORIZATION`; a source or test failure selects new technical work.

**Authority effect:** External contact remains `false`; no issue, PR, email, or comment was sent upstream.

---

## 2026-08-01 — proposed destination is a Forgejo pull request after a controlled fork exists

**Decision:** Use `GitHub fork and pull request` nowhere for this project. The intended path is a controlled Forgejo fork and pull request against `josch/mmdebstrap` `main`, with an issue only when project preference or review clarity calls for one.

**Reason:** The canonical public repository exposes Forgejo issue and pull-request surfaces and its README routes bugs there. Linux Fieldwork has no recorded controlled fork.

**Evidence:** public repository and README review in `SOURCE_MAP.md`.

**Alternatives considered:**

- Debian BTS patch;
- mailing-list series;
- source-only downstream patch;
- issue without code.

**Consequences:**

- identities remain `NEEDS FORK` and `NEEDS BRANCH`;
- packet keeps both issue and PR drafts;
- any fork creation or public submission requires explicit authorization.

**Reopen trigger:** maintainers publish different contribution instructions or the repository owner selects a different delivery method.

**Authority effect:** No controlled fork was created and no public action occurred.

## Interim disposition

`ACTIVE` as of 2026-08-01.

The canonical patch and historical evidence are selected. Current public source identity matches the imported base. Fresh zero-fuzz application, focused execution, and controlled-fork complete-diff review remain before `READY FOR AUTHORIZATION`.
