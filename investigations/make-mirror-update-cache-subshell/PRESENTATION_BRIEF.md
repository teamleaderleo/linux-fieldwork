# Presenting the make_mirror update_cache lifecycle repair

Audience: maintainers, reviewers, Debian/Linux engineers, and non-specialists who need to understand why PRs #286 and #324 exist, what they prove, and where the conclusion ends.

Status: `post-merge explanation and review brief`

## 30-second version

`make_mirror.sh` builds a fresh local Debian package cache in the background. One worker function had a combined signal-and-cleanup trap. When that worker was interrupted, it could kill a proxy owned by its parent, clean temporary APT state twice, continue with later commands, and report success.

The repair was split into two stages:

1. PR #286 gave the worker one cleanup owner, one finalizer, explicit signal statuses, and clear result precedence.
2. PR #324 handled a second timing window: a signal arriving while cleanup was already running. It retains the first handled signal, ignores later handled signals, completes bounded cleanup, and preserves the strongest result.

The patches passed deterministic real-shell regressions and repository-wide CI. The result is intentionally narrow: it proves owner-PID signal handling and bounded cleanup, not whole-process-group cancellation or escalation for a stuck cleanup.

## One-sentence takeaway

A cancellation path must preserve **ownership, first-event identity, cleanup completion, and final-result ordering**; a cleanup command by itself is not a complete signal policy.

## The component in the larger system

### What mmdebstrap is

`mmdebstrap` is an APT-based tool for creating Debian root filesystems. Its test suite builds local mirrors and cache generations so many bootstrap modes can run reproducibly without repeatedly downloading the same package set.

### What make_mirror.sh does

The helper fills one of two cache directories and switches a symlink only after the new cache is ready. The goal is atomic publication: an interrupted run should leave the previously good cache visible rather than expose half-written output.

### What update_cache() does

`update_cache()` creates a temporary APT root below the new cache, reads repository configuration, downloads package indexes and packages, cleans the temporary APT state, and returns its result through a pipeline.

Because it is the final command in a pipeline and is written with parentheses, it runs in a subshell. The worker and the top-level script therefore have distinct process and resource ownership:

| Owner | Resource or responsibility |
| --- | --- |
| top-level `make_mirror.sh` | cache proxy process, proxy PID, final cache lifecycle |
| `update_cache()` subshell | temporary APT root and worker result |

The original trap ignored that distinction.

## The original failure

The imported worker used:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

This short line combined several decisions that should have been separate.

### Ownership failure

The worker killed `$PROXYPID`, but the top-level process created and owned that proxy. A child cleanup path was operating on its parent's resource.

### Termination failure

A shell trap runs commands and then normally returns. Cleanup does not itself mean “stop.” Depending on signal delivery and foreground-child timing, the shell can resume the interrupted workflow after the trap returns.

### Re-entry failure

The successful path called `cleanupapt` and only afterward cleared the EXIT trap. If cleanup failed under `set -e`, EXIT handling could run cleanup again.

### Result failure

The trap did not define which result should win when ordinary work, a signal, and cleanup each had a status. Cleanup noise could obscure the reason the operation stopped.

### Cleanup-time signal failure

The first repair initially cleared INT, QUIT, TERM, and EXIT to their defaults before cleanup. A second signal during cleanup could terminate the shell, replace the first cancellation reason, and leave cleanup partial.

Ordinary EXIT cleanup had a related but different problem: ignoring all signals immediately would make a newly arriving cancellation disappear and could return success.

## Failure timeline for a non-specialist

A useful way to present the baseline is as an event sequence:

```text
worker starts temporary APT work
→ supervisor sends TERM to the worker
→ shell waits for or returns from a foreground command
→ cleanup trap runs
→ worker kills the parent's proxy
→ cleanup runs
→ trap returns instead of terminating
→ later worker code can continue
→ EXIT may run cleanup again
→ final status can be 0
```

For the cleanup-time race:

```text
TERM chooses status 143
→ cleanup begins
→ traps have been reset to default
→ INT arrives
→ shell dies from INT
→ first result 143 is lost
→ cleanup stops halfway
```

The repair makes both timelines explicit rather than relying on incidental shell behavior.

## The two-stage repair

## Stage 1: PR #286 — define ownership and the common finalizer

Patch 0001:

- removes proxy signalling from the worker;
- gives the parent sole proxy stop-and-wait responsibility;
- separates EXIT from INT/QUIT/TERM handlers;
- converts signals to conventional statuses 130/131/143;
- routes every completion path through `update_cache_finish`;
- clears EXIT before cleanup to prevent re-entry;
- runs cleanup once;
- preserves ordinary or explicit-signal failure over cleanup failure;
- verifies immediate rerun.

Stage-1 precedence:

```text
ordinary or explicit-signal failure > cleanup failure > success
```

## Stage 2: PR #324 — retain signals accepted during cleanup

Patch 0002 adds one cleanup-signal status slot.

For ordinary cleanup:

1. install INT/QUIT/TERM recorder traps;
2. clear EXIT;
3. run cleanup;
4. ignore handled signals before reading the final state;
5. return work failure, recorded cleanup-time signal, cleanup failure, or success.

For explicit-signal cleanup:

1. store the already selected signal status;
2. ignore later handled signals;
3. enter the common finalizer;
4. complete bounded cleanup;
5. preserve the first result.

Final precedence:

```text
existing ordinary or explicit-signal failure
> first signal recorded during ordinary cleanup
> cleanup failure
> success
```

## Why that precedence is defensible

### Existing ordinary failure first

The operation already failed before cleanup began. A later cleanup-time signal does not erase that completed result.

### Explicit signal failure first

A signal handler has already accepted and classified a cancellation. Later handled signals during cleanup should not replace it.

### First ordinary-cleanup signal next

If ordinary work succeeded and cancellation arrives during cleanup, returning success would lie. The first accepted signal becomes the primary result.

### Cleanup failure after that

When work succeeded and no signal arrived, cleanup failure is the strongest available failure and should remain visible.

### Success last

Success means work succeeded, no handled signal was accepted during cleanup, and cleanup succeeded.

## Why the approach was split instead of written as one large repair

The first issue was already large enough to contain distinct ownership, termination, re-entry, and result-precedence questions. The second issue became visible only after reviewing what happened inside the common finalizer.

Splitting the work provided:

- a stable baseline with its own losing controls;
- a clear statement of what #286 did and did not prove;
- a smaller second patch focused on trap ordering during cleanup;
- separate execution receipts;
- the ability to reject or revise the second policy without reopening parent/worker ownership;
- durable history showing how review deepened the model.

This is an example of productive staged repair rather than evidence that the first review was useless. Each stage narrowed an untested lifecycle interval.

## Historical precedent inside Linux Fieldwork

The same defect family appeared in `run_qemu` lifecycle work.

A prior candidate preserved a primary result but reset handled signals to default before cleanup. A deterministic TERM-then-INT control showed:

- the second signal replaced the first;
- cleanup stopped after its first action;
- temporary state remained.

That work produced reusable notes now applied here:

- a cleanup-only signal trap does not necessarily terminate the shell;
- first handled signal identity must remain stable through bounded cleanup;
- ordinary EXIT cleanup and explicit-signal cleanup require different signal treatment;
- process-group delivery is distinct from owner-PID delivery;
- deterministic barriers are stronger than sleep-based race tests.

The broader repository now contains several related lifecycle investigations: top-level `make_mirror` proxy cleanup, `run_qemu` result precedence, QEMU image publication, coverage backend process groups, and shell cleanup re-entry. The recurring lesson is to model ownership and event order, not merely add a larger trap.

## Broader Unix and shell context

### Traps are deferred around foreground commands

POSIX shells may defer trap execution while waiting for a foreground utility. That means a parent-only signal can be handled only after a child command returns, and a cleanup-only handler can then return to later shell code.

### Signal delivery topology changes the result

A terminal often sends a signal to a foreground process group. A supervisor or test may signal only one PID. Those are different experiments:

- owner-PID signal: shell receives the signal; child may continue;
- process-group signal: shell and cleanup child may receive it;
- escaped descendant: a child in another group or session may survive both.

PR #324 deliberately proves only the first model.

### Ignored signal dispositions affect children

When a shell ignores a signal before launching a cleanup command, the child may inherit that disposition. That can help bounded cleanup finish, but it is unsuitable as a universal answer for long-running or hostile cleanup.

### Conventional statuses are an interface

Statuses 130, 131, and 143 are `128 + signal number` for INT, QUIT, and TERM. They give shell callers and CI a stable cancellation classification without requiring every caller to inspect direct signal termination.

## Why this approach instead of alternatives

## Alternative 1: keep the original combined trap

```sh
trap 'kill child; cleanup' EXIT INT TERM
```

Why it loses:

- combines parent and worker ownership;
- cleanup can run more than once;
- signal handler can return and resume work;
- no explicit result ordering;
- no first-signal policy.

## Alternative 2: clear all traps to default before cleanup

```sh
trap - EXIT INT QUIT TERM
cleanup
exit "$status"
```

Why it loses:

- a second signal can interrupt cleanup;
- the first signal result can be replaced;
- partial state can affect rerun.

## Alternative 3: ignore all handled signals whenever cleanup begins

```sh
trap '' INT QUIT TERM
trap - EXIT
cleanup
```

Why it loses for ordinary EXIT cleanup:

- no signal result exists yet;
- cancellation during cleanup can disappear;
- successful work plus ignored TERM can return 0.

It is appropriate only after a signal result has already been retained, or while ordinary cleanup has recorder traps installed.

## Alternative 4: re-raise the original signal after cleanup

Possible shape:

```sh
trap - TERM
kill -TERM "$$"
```

Advantages:

- preserves direct signal termination;
- can preserve signal-specific supervisor behavior.

Costs and open work:

- must unblock and restore signal disposition correctly;
- still needs first-signal recording during cleanup;
- complicates precedence with pre-existing ordinary failure;
- may affect portability and shell behavior;
- can change core-dump or wait-status semantics.

The selected `128 + signal` interface matches the existing shell contract and keeps precedence explicit.

## Alternative 5: terminate the entire process group

Advantages:

- can reach foreground descendants;
- can prevent a wrapper child from continuing after parent cancellation.

Why it was separated:

- expands the ownership surface;
- requires safe group creation and registration;
- must handle escaped descendants and PID/group reuse;
- needs wait, timeout, survivor diagnostics, and escalation policy;
- can signal unrelated work if grouping is wrong.

The coverage process-group investigation owns that broader class.

## Alternative 6: TERM, wait, then KILL

Useful for cleanup or descendants that may ignore TERM. It was outside this patch because:

- timeout duration becomes policy;
- KILL prevents cleanup in the target;
- surviving descendants need enumeration and diagnostics;
- the current `cleanupapt` model is intentionally bounded.

## Alternative 7: rollback every effect instead of completing cleanup

The worker cleanup removes temporary APT state. Transactional rollback would be a much larger design and would still require signal/result ordering. The current repair finishes the bounded existing cleanup rather than inventing a new cache transaction model.

## Alternative 8: change the imported source directly

Linux Fieldwork imports exact upstream trees for evidence. Editing the import would blur source identity and make later comparisons ambiguous. Explicit patches preserve:

- the exact baseline;
- exact candidate bytes;
- source application order;
- losing and winning controls;
- the option to prepare an upstream packet later after authorization.

## What the tests actually do

The focused tests do not run a full Debian mirror. They extract and execute the relevant shell lifecycle with real `/bin/sh`.

A deterministic `cleanupapt` replacement:

1. writes `start`;
2. creates a `cleanup-ready` marker;
3. waits for a release marker;
4. writes `end`;
5. removes simulated APT state;
6. optionally returns cleanup failure 74.

The test driver can therefore send a signal at the exact lifecycle boundary rather than hoping a sleep lands in the window.

The matrix includes:

- predecessor negative controls;
- explicit TERM then competing INT;
- ordinary cleanup with INT, QUIT, or TERM;
- host failure 42 plus cleanup-time signal;
- cleanup failure 74 plus signal;
- immediate clean rerun;
- exact source assertions;
- zero-fuzz composition of patches 0001 and 0002;
- complete shell syntax;
- repository discovery behavior.

## Evidence table

| Question | Losing behavior | Landed behavior | Evidence |
| --- | --- | --- | --- |
| Who cleans APT state? | worker, sometimes twice | worker once | #286 ownership and cleanup-failure modules |
| Who stops the proxy? | worker trap kills parent-owned proxy | top-level owner | #286 ownership matrix |
| Does a signal stop later work? | worker can resume | later marker absent | #286 signal matrix |
| What status represents INT/QUIT/TERM? | false 0 or direct replacement | 130/131/143 | #286 and #324 matrices |
| Can a second signal replace TERM? | yes, TERM then INT becomes SIGINT | no, first result remains 143 | #324 cleanup barrier |
| Can ordinary-cleanup TERM disappear? | direct termination or ignored cancellation in losing variants | recorded as 143 | #324 ordinary-cleanup controls |
| Can cleanup failure hide work failure? | possible without precedence | work/signal failure remains primary | #286/#324 precedence controls |
| Does interrupted cleanup affect rerun? | partial APT state remains in losing case | immediate clean rerun succeeds | #324 rerun module |
| Are patch bytes tied to exact source? | historical carriers could drift | zero-fuzz two-patch application | both focused modules and changed-patch gate |
| Are tests duplicated by imports? | earlier helper pattern duplicated cases | module reuse and repository runner execute intended cases once | #286/#324 and PR #315 controls |

## What is proven

For the executed Ubuntu `/bin/sh` reduction and owner-PID signal model:

- worker and parent cleanup ownership is separated;
- cleanup runs once;
- later work does not run after handled cancellation;
- INT/QUIT/TERM have explicit statuses;
- first accepted signal remains stable through bounded cleanup;
- ordinary work failure remains ahead of later cleanup-time signal;
- cleanup-time signal remains ahead of cleanup failure;
- cleanup failure remains visible after otherwise successful work;
- temporary APT state is removed;
- immediate rerun succeeds;
- exact patch composition and syntax pass;
- repository-wide CI passes.

## What is not proven

Do not present these as solved:

- full APT and package download behavior with patches applied;
- entire `make_mirror.sh` execution under cancellation;
- terminal-style process-group signal delivery during cleanup;
- cleanup child behavior when it receives the same signal directly;
- foreground descendants that ignore TERM;
- descendants that call `setsid()` or change groups;
- HUP behavior;
- repeated escalation or TERM-to-KILL;
- permanently blocked cleanup;
- all shells and operating systems;
- Debian package acceptance;
- upstream maintainer agreement.

## The most important caveat to say aloud

> We proved the wrapper's result and cleanup policy when signals are delivered to the shell owner. We did not prove that every child in a foreground process group survives long enough for cleanup to complete, nor that TERM-resistant descendants are gone.

This caveat makes the claim credible. It also points directly to the next meaningful experiment instead of weakening the landed result.

## Multiple review passes performed

### Pass 1: source and ownership

Checked imported `make_mirror.sh`, pipeline/subshell shape, proxy ownership, APT-root ownership, and both retained patches.

Result: the patches align cleanup actions with their owners.

### Pass 2: event ordering and precedence

Enumerated ordinary success, ordinary failure, explicit signal, signal during ordinary cleanup, competing signal during explicit cleanup, cleanup failure, and final exit.

Result: the declared precedence matches the code paths and focused controls.

### Pass 3: losing alternatives

Compared combined trap, default-reset cleanup, universal ignore policy, signal re-raise, process-group delivery, escalation, and direct source editing.

Result: the selected patch is the smallest design that satisfies the bounded owner-PID question.

### Pass 4: historical transfer

Compared prior `run_qemu`, top-level `make_mirror`, QEMU lifecycle, and process notes.

Result: the design follows repeated evidence from the same shell lifecycle defect family.

### Pass 5: test authority

Checked deterministic barriers, predecessor controls, exact patch application, rerun, test imports, current test blobs, and the later explicit unittest runner.

Result: the relevant tests remain present and unfiltered on current `main`.

### Pass 6: current-main persistence

Verified PR #324 merged, its four files remain on `main`, and later repository commits are disjoint from the mechanism.

Result: no post-merge code drift was found in the landed unit.

### Pass 7: claim boundary

Compared owner-PID delivery with process-group delivery, bounded cleanup with blocking cleanup, and internal evidence with upstream integration.

Result: the existing evidence boundary is necessary and should remain prominent.

### Pass 8: reader-facing records

Found that the canonical README and cleanup-signal record still described #324 as pending after merge.

Result: post-merge documentation repair required.

## Suggested five-minute presentation

### Slide or section 1 — What this code does

“`make_mirror.sh` builds a new Debian package cache without replacing the working cache until the new one is ready.”

Visual: parent process owns proxy; worker owns temporary APT directory.

### Slide or section 2 — The bad one-line trap

Show:

```sh
trap 'kill "$PROXYPID" || :;cleanupapt' EXIT INT TERM
```

Say: “This line mixes ownership, cleanup, termination, and result policy.”

### Slide or section 3 — The observable failures

- cancellation can become success;
- worker kills parent-owned proxy;
- cleanup can run twice;
- second signal can replace first;
- partial state can affect rerun.

### Slide or section 4 — The two-stage repair

- #286: one owner, one finalizer, explicit statuses;
- #324: retain first signal through bounded cleanup.

Show precedence ladder.

### Slide or section 5 — How we proved it

Show the deterministic barrier:

```text
signal → cleanup-ready → competing signal → release → inspect result/state
```

Mention losing controls, zero-fuzz patch composition, 303-test CI, and immediate rerun.

### Slide or section 6 — What remains open

- process-group delivery;
- TERM-resistant descendants;
- escalation and stuck cleanup;
- full mirror integration;
- upstream decision.

End with: “The repair is complete for one bounded lifecycle question; the remaining questions are different contracts.”

## Suggested 30-second lay explanation

“The script has a manager process and a worker process. The old emergency handler let the worker shut down the manager's helper, clean twice, and sometimes keep working after a stop request. We first separated who owns what and made every stop return a clear result. Then we fixed a smaller race where a second stop request during cleanup could replace the first one or interrupt cleanup. Tests pause cleanup at the exact point, send competing signals, and verify the first result survives, cleanup finishes, and the next run starts clean.”

## Suggested two-minute technical explanation

“`update_cache()` is a pipeline subshell that owns a temporary APT root, while the top-level script owns the cache proxy. The imported `EXIT INT TERM` trap crossed those owners and did cleanup without explicit termination. PR #286 split EXIT from INT/QUIT/TERM, routed all paths through a common finalizer, removed proxy signalling from the worker, and established work-or-signal failure ahead of cleanup failure. Complete review then found that resetting handled signals to defaults before `cleanupapt` opened a competing-signal window. PR #324 adds a cleanup-time status slot: ordinary cleanup installs first-signal recorders before clearing EXIT; explicit signal cleanup stores the chosen status and ignores later handled signals. The final precedence is existing failure, first ordinary-cleanup signal, cleanup failure, success. Deterministic real-shell barriers prove the losing and repaired cases, including immediate rerun. The claim stops at owner-PID signals and bounded cleanup; process-group delivery and escalation remain separate.”

## Questions a reviewer may ask

### Why not let the last signal win?

The first accepted signal initiated the cancellation policy. Allowing later signals to replace it makes the final result timing-dependent and can interrupt cleanup. Escalation should be explicit rather than accidental.

### Why does an earlier ordinary failure beat a later signal?

The work already produced a concrete failure before cleanup. The later signal changes cleanup timing, not the completed primary result. This ordering also avoids hiding actionable product failure behind cancellation noise.

### Why does a cleanup-time signal beat cleanup failure?

When ordinary work succeeded, the signal is the reason the operation was cancelled. Cleanup failure is secondary. The cleanup status remains visible only when no stronger work or signal result exists.

### Why ignore later signals? Is that unsafe?

They are ignored only after the first handled result is retained and only while the existing bounded cleanup completes. The design does not claim this is suitable for an unbounded or hostile cleanup routine.

### Why include QUIT?

The baseline first patch gave INT, QUIT, and TERM explicit conventional statuses. Patch 0002 preserves that established interface through cleanup. Core-dump-oriented QUIT re-raise semantics are outside this chosen shell-status contract.

### Why not test the full mirror immediately?

A full mirror test is slower, network-dependent, and mixes many unrelated failure owners. The reduced harness first proves the shell lifecycle distinction deterministically. A disposable full integration remains useful follow-up evidence.

### Are synthetic tests trustworthy?

They use real `/bin/sh`, real processes, real signals, waits, files, and the exact retained patches. The synthetic part is the bounded `cleanupapt` body, which provides a deterministic barrier. The claim is limited to that lifecycle boundary.

### Could the test itself be racing?

It waits for explicit work-ready and cleanup-ready files, sends signals only after those markers, uses bounded process waits, and releases cleanup only after the competing signal window. This is stronger than relying on fixed sleeps alone.

### Does this modify Debian or upstream mmdebstrap?

No. The imported source remains unchanged. Linux Fieldwork retains internal patches and evidence. Any upstream contact or submission needs a separate authorization decision.

### Has later repository work invalidated the tests?

The merged patch and test blobs remain unchanged. The explicit unittest runner added later filters only three unrelated extension classes, so these focused tests remain in repository discovery.

### Is the problem still present in public source?

The public source generation examined during this review still contains the original combined trap. That supports continued relevance, while any current upstream status must be refreshed before external presentation or contact.

## Questions for a future design review

These are follow-ups, not blockers for the landed bounded result:

1. Should cleanup receive owner-only signals or whole-group signals in real supervisors?
2. Can `cleanupapt` block indefinitely on any supported path?
3. Is a timeout required before escalation?
4. Should QUIT be represented as 131 or re-raised for direct signal semantics?
5. Should the two patches be composed into one eventual upstream patch?
6. Which full mirror workload is the smallest useful integration gate?
7. Does current upstream source or an active patch already change this lifecycle?
8. Which maintainer-facing explanation best separates proven behavior from policy choice?

## Decision statement for humans

The internal decision already made was:

> Accept the two-patch lifecycle model as the canonical Linux Fieldwork result for `update_cache()` owner-PID signals and bounded cleanup.

A future upstream decision would be different:

> Decide whether the same ownership and result policy is appropriate for current mmdebstrap, then validate it in the project's complete test and integration environment.

Those decisions should not be conflated.

## References inside this repository

- [`README.md`](README.md) — complete worker lifecycle and history;
- [`CLEANUP_SIGNALS.md`](CLEANUP_SIGNALS.md) — cleanup-time signal mechanism and receipts;
- [`0001-confine-update-cache-signal-cleanup.patch`](0001-confine-update-cache-signal-cleanup.patch);
- [`0002-retain-signals-through-cleanup.patch`](0002-retain-signals-through-cleanup.patch);
- `notes/processes/signal-traps-must-terminate-after-cleanup.md`;
- `notes/processes/handled-signals-must-remain-stable-through-cleanup.md`;
- `notes/processes/signals-during-exit-cleanup-must-not-disappear.md`;
- `investigations/run-qemu-result-precedence/FIRST_SIGNAL_CLEANUP.md`;
- PR #286 and PR #324;
- issue #231.

## External orientation references

Refresh these before a public presentation because package and branch state can move:

- official mmdebstrap repository and README;
- Debian Sources package page for the relevant mmdebstrap version;
- POSIX Shell Command Language trap and signal-wait semantics;
- shell documentation for signal traps, process groups, and inherited ignored dispositions.

## Final presentation guardrails

Say:

- “The tests demonstrated…”
- “The selected policy is…”
- “The evidence ends at…”
- “A separate follow-up would test…”

Avoid saying:

- “Signals are fully solved.”
- “All children are guaranteed gone.”
- “Cleanup can never hang.”
- “This is already fixed upstream.”
- “The full mirror workload was tested.”
- “The patch is ready to submit externally.”

## Authority

Internal explanation, retained evidence, and candidate history only. External contact authorized: `false`.
