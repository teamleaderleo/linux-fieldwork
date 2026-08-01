# HANDOFF — unit 11 coverage backend cancellation

Date: 2026-08-01  
State: `READY FOR AUTHORIZATION`  
Worker or variant: `GPT-5.6 Thinking`  
Linux Fieldwork branch: `upstream/unit-11-coverage-backend-cancellation`  
Internal review surface: PR #401, ready for review  
Last content head before this handoff commit: `89456fbfa298412ddbab363adc8057a5a28a1c7e`  
External contact authorized: `false`  
External contact made: `none`

## Exact stopping point

The technical unit is complete for its selected responsive-topology claim.

The packet contains:

- upstream-root product patch;
- durable null/source verifier;
- exact canonical Actions carrier;
- current identities and carrier map;
- mechanism, compatibility, rejected alternatives, and reopening triggers;
- exact current-upstream test receipts and artifact digests;
- polished upstream issue and pull-request drafts;
- authorization-ready decision record.

The selected product mechanism is:

```python
proc = subprocess.Popen(argv, start_new_session=True)
...
try:
    os.killpg(proc.pid, signal.SIGTERM)
except ProcessLookupError:
    pass
proc.wait()
print("interrupted by SIGINT", file=sys.stderr)
raise SystemExit(130)
```

The retained patch is:

`upstream-packets/units/11-coverage-backend-cancellation/patches/0001-coverage-own-selected-backend-group.patch`

## Exact identities

- canonical upstream repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- intended branch: `main`;
- exact upstream base executed: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- last upstream commit touching `coverage.py`: `c82fc7e261c7a2fd85e499484108408fd42331d2`;
- canonical/imported `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`;
- canonical `run_null.sh` blob: `e0a8c106f9d3d636baea286d2ab33834748dffc9`;
- canonical `run_qemu.sh` blob: `426aeeb854173569b24e64d6eb85019f45bdf0b6`;
- packet patch blob: `f1a2c75adfa009b6f1ac29e5a31bef526400444f`;
- historical prefixed patch blob: `4f2a749e50d42655ebb6519ca6550d2f666985bc`;
- mechanism carrier: PR #313 `e90fc438f530f7bd78ffd6fd1ba24c665bd96913`;
- refined test carrier: PR #339 `8253ab2ef6fed22b34fc5f5d6d20cda75c25e2c7`;
- refined QEMU test blob: `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa`;
- controlled fork: `NEEDS FORK`.

## Final exact execution receipt

Linux Fieldwork Actions run `30689911760` passed on branch head `83efaa3b3baee05c6b8f96138a3ee619942ce984`.

### Canonical packet-patch job

- job: `91342674259`;
- exact canonical checkout: success;
- canonical/imported source blob equality: success;
- packet patch application with `--fuzz=0`: success twice;
- Python compilation: success;
- six null/source/status controls: 6/6 twice;
- artifact: `8815289674`;
- artifact SHA-256: `25e62dec929f27e628816568d6264f2bee45474c00b00c3c047f53209608ef1d`.

### Canonical refined topology job

- job: `91342674164`;
- exact PR #339 regression carrier materialized: success;
- canonical source and wrappers copied into carrier: success;
- exact test-blob assertions: success;
- null, QEMU-wrapper, and actual passwordless-sudo controls: 14/14 twice;
- no skips;
- first pass: 3.874 seconds;
- immediate rerun: 3.599 seconds;
- artifact: `8815290820`;
- artifact SHA-256: `63634782bfd230129238ee71aa60ad83ae5b43dfcf3291123cfdbd0770bdf63e`.

## Latest distinguishing result

| Variant | Driver status | Nested responsive work before deliberate release | Later work |
| --- | ---: | --- | --- |
| imported baseline | 0 after release | alive | yes |
| status-only predecessor | 130 after release | alive | yes |
| selected group candidate | 130 | no live in-group process | no |

The refined QEMU controls recorded Python SIGINT-handler entry before releasing losing-control survivors. The sudo controls executed as root through passwordless sudo; they did not skip.

## Work completed in the continuation session

1. Confirmed shell DNS remained unavailable.
2. Cross-checked a public mirror and canonical checkout against imported blob `9a5224...`.
3. Added `scripts/test_current_import.py` with source-blob assertion, zero-fuzz application, compilation, and six focused controls.
4. Added the unit-specific Actions workflow.
5. Opened internal PR #401 as the execution and review surface.
6. Ran exact canonical packet-patch controls twice.
7. Ran exact PR #313 null/QEMU/sudo controls twice against canonical source.
8. Re-ran the complete topology matrix using PR #339's handler-entry refinement.
9. Recorded exact jobs, source blobs, patch blobs, test blobs, artifacts, digests, cleanup, and rerun results.
10. Promoted the packet and index to `READY FOR AUTHORIZATION`.
11. Marked internal PR #401 ready for review.
12. Made no upstream contact.

## First incomplete step

Human decision: choose `SEND` or `HOLD`.

A `SEND` decision must explicitly authorize:

1. creation or use of a controlled mmdebstrap fork;
2. creation of a candidate branch from current canonical `main`;
3. public Forgejo pull-request submission and any related public comments.

## Next safe action before authorization

Review internal PR #401 and the packet diff. Preserve the current state and avoid creating any upstream fork, issue, pull request, review, email, or comment.

## Next action after explicit SEND authorization

1. Refresh canonical `main` and compare it with `77ec9be...`.
2. Create or select the controlled fork.
3. Create the candidate branch from the refreshed exact base.
4. Apply the retained patch with zero fuzz.
5. Re-run the packet verifier and refined topology gate if the base changed.
6. Refresh `UPSTREAM_PR.md` links and exact identities.
7. Submit only the authorized public surface.
8. Record the public reference and submitted commit/patch identity in every packet surface and issue #397.

## Evidence limits

- real QEMU/debvm and prepared-mirror package operations remain outside the focused controls;
- TERM-resistant, deferring, or group-escaping descendants remain outside the selected claim;
- non-Linux behavior remains outside the project/runtime target;
- upstream CI and maintainer review begin after authorized submission.

These limits are recorded and accepted for this narrow unit. Issue #341 retains the stronger cleanup-policy reopening matrix.

## Recovery guide

Read in this order:

1. `README.md`;
2. `TESTS.md`;
3. `DECISIONS.md`;
4. `SOURCE_MAP.md`;
5. retained patch;
6. `UPSTREAM_PR.md`;
7. PR #401.

Use issue #397 for routing. This packet is the durable technical record.

## Authorization boundary

Internal review and packet maintenance may continue. Public upstream interaction requires explicit authorization. No upstream contact occurred.
