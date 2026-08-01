# Source-only submission-shape decision — 2026-08-01

## Decision

Keep the clean controlled target contribution source-only. `coverage.py` is the sole changed file.

Do not add a guessed Python test under `tests/`. Do not add a recursive mini-coverage fixture unless an eligible independent reviewer or upstream maintainer requires it.

## Reason

Every non-dot target `tests/` entry is a shell-template package scenario indexed by `coverage.txt` and dispatched through the outer `coverage.py` harness.

Testing this outer orchestrator from inside that same harness would require a second miniature coverage tree, nested source and wrappers, nested metadata and test inventory, a constructed survivor topology, parent-only signalling, and nested cleanup. That fixture would be substantially larger than the 13-line source hunk and would primarily test its own recursive scaffolding.

## Retained evidence

- exact clean target head `431614b3af58ba4f70791aa1d42cf5b71c965dd2`;
- candidate blob `9e31f21cf37228257b5e0705d9ecb13b7a66e40f`;
- target run `30706007117` proving zero-fuzz and byte equivalence, compilation, 6/6 twice, and 14/14 twice;
- ordinary source run `30706633832` proving native `coverage.sh help man version` 3/3 twice;
- clean internal review surface `teamleaderleo/mmdebstrap#4`, one file, 8 additions and 3 deletions.

## Claim effect

No claim is broadened. The result remains limited to TERM-responsive work that stays in the owned process group.

The full prepared-mirror package matrix remains an evidence limit, not a prerequisite for the narrow source-only lifecycle claim. An eligible reviewer may still require broader execution or a recursive native test.

## Reopen triggers

- eligible review requires a target-native regression;
- upstream contribution policy requires a test in the same change;
- a smaller stable target-native self-test surface becomes available;
- the external reproducer is found not to preserve a consequential target boundary.

## Authority

This is an internal candidate-organization decision. It does not authorize canonical-upstream contact.
