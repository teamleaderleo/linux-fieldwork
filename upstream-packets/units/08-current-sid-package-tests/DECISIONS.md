# Decision log

## 2026-08-01 — compose four sequential package-test corrections

**Decision:** Retain one ordered four-patch upstream-facing series covering Deb822 handling, installed-command identity, current-sid SIGINT delivery, and phase-scoped hook-free scheduling.

**Reason:** These corrections remove sequential blockers from the same Debian autopkgtest entry point. Their composed result reaches the next independent package-test result, while each commit remains individually reviewable.

**Evidence:** Issue #397 unit 08; carrier sequence #119/PR #72, #153/PR #171, #320/PR #326, #350, #357, PRs #354/#359, and PR #361 run 999.

**Alternatives considered:**

- submit each historical LF carrier separately;
- merge all carrier machinery into one broad patch;
- retain only the final scheduler correction.

**Consequences:**

- one merge request can present the complete current-sid package-test progression;
- the series remains easy to split by commit if maintainer review requests smaller delivery units;
- every LF-only evidence mechanism stays outside the upstream diff.

**Reopen trigger:** Current Salsa overlap or exact-head testing shows one correction already landed, disproved, or independently reviewable with no ordering dependency.

**Authority effect:** Internal composition only. External contact remains unauthorized.

---

## 2026-08-01 — remove the installed-command proxy from delivery

**Decision:** Exclude the formatted Perl proxy and distill its command-identity result to `/usr/bin/mmdebstrap` in `debian/tests/testsuite`.

**Reason:** The proxy enabled historical reduction runs, yet it redirected formatter, lint, and POD preflight to temporary proxy source. Its relative form also failed after a directory change. The package test seeks the installed Debian binary, whose stable path is `/usr/bin/mmdebstrap`.

**Evidence:** PR #72 review boundary and cwd-changing run receipts; imported testsuite command path; carrier repair using an absolute temporary proxy.

**Alternatives considered:**

- retain `CMD=mmdebstrap` and rely on `PATH`;
- install a temporary absolute proxy;
- change `coverage.py` command resolution globally.

**Consequences:**

- upstream source receives one direct command-path hunk;
- the newly distilled hunk requires fresh exact-head validation because historical real-sid execution used an absolute temporary proxy.

**Reopen trigger:** Upstream package layout differs, maintainers require path lookup, or focused preflight reveals a direct-path incompatibility.

**Authority effect:** No external authority change.

---

## 2026-08-01 — select dash builtin process-group SIGINT

**Decision:** Use `/bin/dash -c 'kill -s INT -- "$1"' dash "$pgid"` in `tests/sigint-during-customize-hook`.

**Reason:** The current-sid probe showed status-zero whole-group delivery for this spelling under the real `set -e` constraint. External procps long and short `--signal`/`-s` forms rejected the negative group target in that environment.

**Evidence:** PR #326 exact sid run `30635739060` / 10, artifact `8795229704`, digest `sha256:60daebe3f700d384c15414a1d6f5317532c2c73b22f863eef0dda730a978a529`.

**Alternatives considered:**

- external compact `/bin/kill -INT -- -PGID`, also successful in the probe;
- Python `os.killpg`, successful as a control;
- retain external long `--signal` syntax.

**Consequences:**

- shell implementation and syntax are explicit;
- compatibility claim stays bounded to current Debian sid/Linux with dash.

**Reopen trigger:** Current Salsa changes the test topology or a fresh sid gate produces a different status/topology result.

**Authority effect:** No external authority change.

---

## 2026-08-01 — scope `tar1.txt` to each execution phase

**Decision:** Mark only `root-without-cap-sys-admin` as the hook-free hard consumer, prepend exact prerequisite `create-directory` to the focused invocation, and permit broad coverage to execute `create-directory` again.

**Reason:** Run 974 proved the focused pair passed and also proved that broad consumers require a broad-hook baseline. A producer marked hook-free-only leaked a plain baseline into host-hook comparisons.

**Evidence:** PR #72 run 974; PR #359 accepted patch and CI 995; PR #361 run 999.

**Alternatives considered:**

- move the consumer to the soft phase and map every failure to 77;
- mark both producer and consumer hook-free-only;
- share one `tar1.txt` across phases;
- duplicate fixture logic inside the consumer.

**Consequences:**

- focused capability failures remain authoritative;
- broad consumers receive the correct hook-specific baseline;
- fixture production remains centralized in `tests/create-directory`.

**Reopen trigger:** Upstream removes shared `tar1.txt`, changes producer order, or introduces several hook-free consumers with different prerequisites.

**Authority effect:** No external authority change.

---

## 2026-08-01 — pin executable evidence to Debian 1.5.7-3 and hold live-master claims

**Decision:** Use imported exact revision `debian/1.5.7-3` / `6fde999741f4fe1e7bf38079acf29432ef87a35e` as the current executable base, while requiring a live Salsa `master` refresh before readiness.

**Reason:** The import identity is exact and matches the current sid source-package version observed during this pass. The environment could read public project/package pages but could not materialize the live Salsa tree for application and overlap review.

**Evidence:** `upstream/mmdebstrap/.linux-fieldwork-source.json`; official Debian package and Salsa project pages recorded in the work session.

**Alternatives considered:**

- claim current `master` from the imported package tag;
- postpone all packet composition until live network access exists;
- use an unrelated GitHub mirror as canonical source.

**Consequences:**

- the packet has a precise reproducible source base now;
- `READY FOR AUTHORIZATION` remains unavailable until the live refresh and exact distilled-series gate pass.

**Reopen trigger:** A worker with Salsa checkout access fetches current `master`, records its commit, and completes overlap/application testing.

**Authority effect:** External contact remains unauthorized.

---

## 2026-08-01 — make the complete series one executable repository gate

**Decision:** Add `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` as the canonical internal series-application gate.

**Reason:** The packet previously carried a manual command only. A repository test can apply the series twice to fresh imported-source copies, reject fuzz/offset, compile and parse all transformed files, prove deterministic candidate bytes, and verify the imported source stays unchanged.

**Evidence:** Gate commit `7782872ae2f731a27ed672df3a37b1d3b1581aa4`; syntax-only receipt `py_compile=PASS`, `ast_parse=PASS`, source SHA-256 `a16b060b02a7c9e1b43db600f0f5789e6e5fc3add7cf93dc95ca32ad314b3dd6`.

**Alternatives considered:**

- leave the manual command as the sole gate;
- create another packet-specific workflow;
- mutate the imported source directly on the packet branch.

**Consequences:**

- ordinary Linux Fieldwork CI can execute the complete series once a PR or workflow-dispatch path is available;
- no new workflow or privileged execution surface is introduced;
- the exact series remains unproved until the test runs against a full checkout.

**Reopen trigger:** The test proves too expensive, duplicates an accepted generic packet gate, or exact execution reveals a missing source file or false receipt assumption.

**Authority effect:** Internal test work only. A blocked draft-PR creation was treated as a connector event and was not retried; external-contact state remains unchanged.

## Final disposition

`ACTIVE` on 2026-08-01. The upstream-facing series, full packet, and executable exact-series gate exist. Gate execution, focused execution, current-sid package execution, and live Salsa-master refresh remain open.
