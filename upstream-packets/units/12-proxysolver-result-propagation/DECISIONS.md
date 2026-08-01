# Decision log

## 2026-07-31 — compose ordinary and signal repairs into one source patch

**Decision:** Retain one patch containing the PR #134 ordinary-status repair and the PR #207 signal-identity repair.

**Reason:** Both changes implement the same completed-child result decision, depend on the same explicit wait, and touch adjacent source lines. Either component alone leaves a known incorrect result.

**Evidence:** Issues #133 and #165; PRs #134, #166, #207; `DEEP_DIVE.md`; composed patch SHA-256 `74819e72482afe00abc3d4c7678a4f91cdbef61f3e2519296755a3a9fa049c48`.

**Alternatives considered:**

- ordered two-patch series, rejected because the first patch is knowingly incomplete as a final contract;
- preserve only ordinary results, rejected by SIGTERM/SIGINT negative controls;
- preserve only signal results, impossible without first recording the child result.

**Consequences:** Reviewers receive one bounded source diff and one result matrix.

**Reopen trigger:** Upstream requests separable commits or current source overlap makes one patch harder to review.

**Authority effect:** Internal composition only; external contact remains unauthorized.

---

## 2026-07-31 — preserve POSIX signal identity through exact replay

**Decision:** Restore/unblock the child signal and signal the wrapper itself instead of mapping to `128 + signum`.

**Reason:** Exact replay preserves the POSIX signaled result observed by a parent. Numeric shell mapping exits normally and loses that identity.

**Evidence:** ordinary-only SIGTERM 241 and SIGINT 254 versus candidate `-SIGTERM` and `-SIGINT`; blocked-SIGTERM control; PR #207 review.

**Alternatives considered:**

- `128 + signum`, rejected for this faithful-result contract;
- negative `SystemExit`, rejected because modulo-256 truncation is accidental and misleading.

**Consequences:** The candidate uses Linux/POSIX `pthread_sigmask`; output closure and explicit stdout flush precede replay; code after replay cannot own cleanup.

**Reopen trigger:** Upstream policy prefers normal exits, portability beyond POSIX, or a supervisor contract requires numeric mapping.

**Authority effect:** Internal technical decision only.

---

## 2026-07-31 — use PR #207 as canonical signal component evidence

**Decision:** Treat PR #166 as historical development and PR #207 as the canonical clean signal evidence carrier.

**Reason:** PR #207 transferred the exact four reviewed blobs onto current main and merged after successful current-main execution. PR #166 was retired as stale and unmergeable.

**Evidence:** PR #166 head `50fdbcd25b51842ff2b489a91e36668e0e2340ea`; PR #207 head `e4b16f5180e8bf67bf58621cac4447f4a4a55f44`; merge `72f4d27aadf1863ee1b534d9751f3061c55b2ba4`; CI `30579889333`.

**Alternatives considered:** retain PR #166 as canonical, rejected by its explicit retirement receipt.

**Consequences:** Source maps retain #166 for approach history and route current evidence through #207.

**Reopen trigger:** Blob comparison shows divergence or a later carrier supersedes #207.

**Authority effect:** None.

---

## 2026-07-31 — keep parent-interruption lifecycle outside unit 12

**Decision:** Unit 12 covers the result of a solver that has completed. Wrapper interruption while a child remains active stays separate.

**Reason:** That path requires signal handlers, forwarding/process-group policy, and cancellation cleanup ownership. Combining it would widen a small result-propagation review.

**Evidence:** PR #134 review identified the lifecycle gap; unit #397 boundaries assign adjacent lifecycle work to other units.

**Alternatives considered:** add parent-signal forwarding here, rejected as a different operation owner and timeline.

**Consequences:** The upstream draft states this exclusion directly.

**Reopen trigger:** Current upstream already has a parent-signal handler in `proxysolver`, or maintainers require a single lifecycle change.

**Authority effect:** None.

---

## 2026-07-31 — remain ACTIVE pending exact current-upstream execution

**Decision:** Keep the unit `ACTIVE`.

**Reason:** The composed patch and local matrix are strong, while the exact upstream checkout, source-byte comparison, native placement, native test gate, controlled fork, and candidate head remain absent.

**Evidence:** `TESTS.md` executed and unexecuted gates; public upstream main `77ec9be5417ee44c96343d2347145585da1b1f94`.

**Alternatives considered:** `READY FOR AUTHORIZATION`, rejected because technical preparation still has named executable steps.

**Consequences:** No send/hold decision is requested.

**Reopen trigger:** Exact upstream application and focused/native gates pass on a controlled candidate head.

**Authority effect:** External contact remains unauthorized; none occurred.

---

## 2026-08-01 — retain native test and coverage registration as separate drafts

**Decision:** Store the complete upstream-shaped test as `native-tests/proxysolver-result-propagation` and its registration as `native-tests/coverage.txt.stanza`; defer a source-tree test patch until exact canonical `coverage.txt` context is materialized.

**Reason:** Public harness inspection resolves the required file shape and registration contract, while the current environment still lacks canonical checkout bytes. A context-bearing `coverage.txt` hunk created now would guess at insertion context and could become stale or malformed.

**Evidence:** `artifacts/2026-08-01-native-gate-selection.md`; native test SHA-256 `3505be52c6feec272c3fc177fb49e7c19bb326167f2013944f0494b685b20dd5`; candidate PASS twice and after restoration; imported baseline expected FAIL at `('exit-7', 0, 7)`; `/bin/sh -n` and candidate `py_compile` PASS.

**Alternatives considered:**

- emit an approximate `0002` patch now, rejected because exact `coverage.txt` context is unavailable;
- keep only the packet-specific unittest, rejected because the upstream harness boundary is now understood and a project-shaped test adds review value;
- run the full coverage suite, deferred because the canonical checkout and its mirror prerequisites remain unavailable.

**Consequences:** The packet now contains copy-ready native test material and a precise focused command, while accurately separating local direct-gate evidence from unexecuted canonical `coverage.py` evidence.

**Reopen trigger:** Exact canonical checkout becomes available; then place both drafts, generate the real integration patch, and run the selected coverage test.

**Authority effect:** Internal branch files only. No fork or upstream message was created.

## Final disposition

`ACTIVE` as of 2026-08-01. Native placement and a discriminating project-shaped test are now prepared and locally validated. The first incomplete step remains exact canonical source verification and patch execution, followed by exact-context test placement and the focused `coverage.py` gate.
