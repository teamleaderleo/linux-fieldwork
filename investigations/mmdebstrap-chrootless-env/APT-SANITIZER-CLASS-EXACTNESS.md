# Exact chrootless flag for the APT sanitizer receipt

## TL;DR

Merged PR #368 retains the exact expected APT-managed outer-mutation argv:

```text
env -i PATH=... TMPDIR=... dpkg --force-not-root --force-script-chrootless --root=... --install ...
```

Its shared classifier labels any structurally selected `env -i ... dpkg` call as `sanitizer-dpkg`. That is broader than the written claim and broader than the direct-transaction receipt, which already requires exact `--force-script-chrootless` element membership.

This current-main follow-up requires all three properties before assigning the sanitizer class:

1. `env` ignores the inherited environment;
2. the structurally selected command basename is `dpkg`;
3. the exact command argument `--force-script-chrootless` is present.

No product patch, transaction command, package fixture, workflow, or imported source changes.

## Explain like I'm five

The receipt was labeling every clean-room delivery truck as *the package-script truck*. The real truck also carries a specific badge: `--force-script-chrootless`.

The repair checks the badge as its own argument. A sticker that merely contains the same words does not count.

## Why care

The APT transaction's raw evidence is strong, but automation should enforce the same boundary the report describes. Otherwise an unrelated `env -i dpkg --version` call could satisfy the class count while the governed chrootless package-script launch changed or disappeared.

Exact-element matching also prevents a look-alike argument such as:

```text
prefix--force-script-chrootless-suffix
```

from being promoted to authority evidence.

## Landing race and current-main ownership

The focused stack PR #374 passed:

- Linux Fieldwork CI `30650262134` / 1022;
- dedicated chrootless workflow `30650262141` / 115.

PR #374 was composed into PR #368's branch, but a parallel squash merged PR #368 to main from its preceding head. Direct inspection of the landed main tree showed the broad classifier remained. This file and its two code/test companions are therefore a post-merge follow-up, not part of PR #368's landed claim.

Authoritative landed product commit:

- PR #368 merge `8c83a739d9330418479a01bbef77d71bfc2dfbd7`.

Green predecessor evidence:

- PR #368 current-head CI `30650101464` / 1021;
- dedicated workflow `30650100748` / 114;
- artifact `8801028296`, digest `sha256:d8cad7c419c8982ce75bc5e7e6fb47ee6c246a283092a61defc9e4d41c225676`.

The first current-main follow-up PR #375 passed repository CI 1023 and dedicated chrootless gate 116. Main then moved by disjoint Packet B receipt work and its generated merge lacked a fresh workflow receipt. This v2 carrier recreates the same three blobs directly on that newer main generation rather than treating disjointness as execution evidence.

The earlier final artifact also retained the exact expected argv. This follow-up changes only what the automated shared class accepts.

## Repair and controls

Changed files:

- `tools/classify_env_argv.py`;
- `tests/test_classify_env_argv.py`;
- this record.

Focused controls require:

- exact chrootless sanitizer → `sanitizer-dpkg`;
- dpkg without ignore-environment → not sanitizer;
- `env -i dpkg --version` → not sanitizer;
- substring look-alike flag → not sanitizer;
- shell text mentioning the flag → still host hook;
- `env -S` second parser → not guessed;
- directory summary still retains all four classes.

## Evidence boundary

The class remains structural rather than target-specific. It does not validate the exact root, TMPDIR, PATH, package path, or complete dpkg option order. Those values remain retained in raw argv and are cross-checked by transaction success, maintainer-script PATH observations, explicit configured/empty path controls, source identity, and equal installed package sets.

A future claim depending on one exact target or complete argv ordering should add a transaction-specific schema rather than silently overloading the shared class.

## Disposition

`CURRENT-MAIN POST-MERGE EVIDENCE REPAIR` until fresh repository CI and the dedicated chrootless workflow pass on this exact head. Then merge locally and verify the landed main blob directly.

Internal Linux Fieldwork work only. No external contact is authorized or included.
