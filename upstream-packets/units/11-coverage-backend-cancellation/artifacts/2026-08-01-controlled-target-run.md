# Controlled target execution — 2026-08-01

## Result

The selected `coverage.py` repair now exists on a clean controlled target branch and passed an exact target-repository execution gate. The former `NEEDS FORK` and focused target-execution blockers are cleared.

## Clean source identity

- controlled repository: `teamleaderleo/mmdebstrap`
- canonical snapshot base: `77ec9be5417ee44c96343d2347145585da1b1f94`
- base `coverage.py` blob: `9a522484aef05deae514a98e4b6adf5feb6c886d`
- clean source branch: `linux-fieldwork/unit-11-coverage-backend-cancellation`
- clean source head: `431614b3af58ba4f70791aa1d42cf5b71c965dd2`
- candidate `coverage.py` blob: `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`
- clean diff: one commit; `coverage.py` only; 8 additions and 3 deletions

The source commit contains no Fieldwork notes, fixtures, workflows, or research files.

## Internal execution surface

- internal controlled-fork PR: `teamleaderleo/mmdebstrap#2`
- PR base: `linux-fieldwork/upstream-main-snapshot@77ec9be5417ee44c96343d2347145585da1b1f94`
- runner branch/head: `linux-fieldwork/unit-11-coverage-backend-cancellation-runner@f0319d53f515174c3794237f34f76699182ac509`
- generated merge tested: `bf1f0cfde0ec6e0691c0dfb7d4656aafe3deab48`
- workflow run: `30706007117`
- result: success

### Candidate equivalence and null

- job: `91385135488`
- exact base/source/blob/packet identities: success
- packet patch `f1a2c75adfa009b6f1ac29e5a31bef526400444f` applied with zero fuzz
- materialized patch result was byte-identical to target `coverage.py`
- target candidate compiled
- packet matrix: 6/6 in 1.421 seconds
- immediate rerun: 6/6 in 1.420 seconds
- artifact: `8820336271`, `unit-11-target-null-gate`
- artifact SHA-256: `97eba28273b50dfcf51c32a2fe4cf49aa50da5634a3aaba6b052ad3728ae1ce8`
- artifact expiry: 2026-10-30

### Refined topology

- job: `91385135449`
- exact PR #339 carrier and regression blobs: verified
- Python compilation: success
- null/QEMU-wrapper/passwordless-sudo matrix: 14/14 in 4.246 seconds
- immediate rerun: 14/14 in 4.367 seconds
- skips: none
- actual passwordless-sudo controls: executed
- refined QEMU test blob: `0c2a050faf8e98320fc0c4fe4634d46bdf7f0dfa`
- artifact: `8820337503`, `unit-11-target-refined-topology-gate`
- artifact SHA-256: `8d72b079fa9e30ee92bdf28cf217e9df3e4ae7a5ffeb7374b76950313bf24614`
- artifact expiry: 2026-10-30

Both jobs uploaded receipts and completed runner orphan-process cleanup.

## Target test-layout decision

The canonical project declares its ordinary suite through `make_mirror.sh`, `coverage.sh`, `coverage.py`, `coverage.txt`, and shell-template entries under `tests/`. `coverage.py` rejects non-dot `tests/` entries that lack matching `coverage.txt` records. A guessed Python unit-test file under `tests/` would therefore violate the target's suite inventory and be consumed through the wrong runner.

No fake target-native test path is claimed. The focused regression remains in the exact internal carrier until a real target harness integration is designed or explicitly declined.

## Remaining work

- select an actual target-native regression integration or record a deliberate source-only submission decision;
- run the project-declared mirror-backed/source ordinary gate at clean source head `431614b3...`;
- decide whether to close/delete the isolated runner after evidence transfer;
- obtain eligible independent complete-diff acceptance for the clean source branch;
- refresh public overlap and contribution-policy checks before any authorized submission;
- obtain explicit public-contact authorization.

## Authority

The controlled fork, branches, internal PR, and Actions run are internal preparation. No canonical-upstream issue, pull request, merge request, review, email, or comment was created.
