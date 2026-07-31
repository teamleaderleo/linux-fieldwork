# Foreground cancellation topology stop receipt

Date: 2026-07-31

Owning issue: #263. Research carrier: PR #264.

## TL;DR

The investigation proved that prompt owner-only and worker-only cancellation is technically possible, but requires several separate ownership mechanisms plus process-group dependencies. The remaining latency has not been measured as harmful, while the accepted top-level and worker repairs already provide correct eventual status and cleanup.

Disposition: `HOLD` source expansion and retain the negative/comparative evidence.

## Exact evidence set

Canonical branch paths:

- `README.md` — stop decision and evidence summary;
- `CALLER_TOPOLOGY.md` — why caller-group delivery is not a repository guarantee;
- `COMMAND_INVENTORY.md` — exact source grammar and minimum primitives;
- `OUTPUT_PIPELINE.md` — final-PID rejection and viable isolated-group output contract;
- `FALLBACK_CHAIN.md` — fallback, cancellation, cleanup precedence, and errexit control;
- five focused test modules covering 21 controls.

## Changes made in the final exploration round

- added the complete output-capture contract with output, status, cancellation, cleanup, and rerun controls;
- added the seven-case fallback ownership and cleanup-precedence matrix;
- found and retained the `set -e` helper mutation negative control;
- removed duplicate output and fallback records/tests created by parallel overlap;
- aligned the canonical records on one stop decision.

## Executed focused gates

Locally executed:

```text
python3 tests/test_make_mirror_output_capture_pipeline_contract.py -v
python3 tests/test_make_mirror_fallback_child_ownership.py -v
```

Results:

- output-capture contract: 4/4 passed;
- fallback ownership contract: 7/7 passed;
- Python compilation of the fallback matrix passed;
- immediate rerun controls passed inside both matrices.

Earlier retained local matrices on the same carrier cover:

- foreground topology/source: 6 controls;
- parent pipeline PID/input/status: 2 controls;
- output pipeline negative/group ownership: 2 controls.

Hosted exact-head repository CI remains required before the PR itself can close or merge as retained internal evidence.

## Complete-diff review

The final carrier contains tracked records and model tests only. It changes no imported source, retained product patch, workflow, dependency declaration, or external interaction.

Parallel overlap was reconciled:

- `OUTPUT_PIPELINE.md` is the single canonical output-pipeline record;
- `tests/test_make_mirror_output_capture_pipeline_contract.py` is the complete semantics contract;
- `tests/test_make_mirror_output_capture_pipeline_ownership.py` retains the negative final-PID and positive isolated-group topology;
- `tests/test_make_mirror_fallback_child_ownership.py` is the single canonical fallback matrix;
- duplicate output and fallback files were removed.

## Cleanup and rerun

All new controls use disposable temporary directories. Cancellation tests terminate and reap held children, remove private captures, publish no partial result, and perform an immediate clean rerun.

## Composition and overlap

- PR #224 remains the accepted top-level proxy lifecycle owner;
- PR #259 remains the focused `update_cache()` eventual status and cleanup owner;
- PR #264 is comparative research only and supplies no overlapping product patch;
- caller-owned group delivery remains optional operational guidance, not a source contract.

## Remaining caveats

- no real APT workload or latency distribution;
- no full mirror, network, QEMU, package, or privileged execution;
- no cross-host dependency proof for `setsid` and group-aware external `kill`;
- no composed launch-registration or competing-first-signal implementation;
- no timeout or TERM-to-KILL escalation.

## Reopening triggers

Reopen only after measured harmful latency, a supported isolated-supervisor contract, explicit acceptance of process-group dependencies, or contradictory lifecycle evidence.

## Authority

Internal Linux Fieldwork work only. No external contact is included or authorized.
