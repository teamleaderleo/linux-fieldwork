# Lossless direct chrootless `env` and `dpkg` argv receipts

## TL;DR

The current-main chrootless authority candidate already executes the direct Essential-package transaction successfully. Its fake caller-path `env` and fake caller-path `dpkg` wrappers still joined argv through `$*`, then classified sanitizer and chrootless ownership with substring greps.

This repair gives the direct path the same evidence discipline as the accepted apt-managed repair:

- one NUL-delimited argv record per fake-wrapper process;
- exact parsed `env` classes;
- exact `dpkg` argv vectors;
- exact-element matching for `--print-architecture` and `--force-script-chrootless`;
- retained JSON receipts for every candidate and mutation case.

The two product patches, Essential package fixture, repository, and transaction commands are unchanged.

## Explain like I'm five

The old notebook wrote every argument as one sentence. If one filename merely contained the words `--force-script-chrootless`, the checker could mistake that filename for the real option.

The repaired notebook keeps every argument in its own box. It asks whether one whole box equals the option, not whether the words appear somewhere in the sentence.

## Why care

The direct transaction makes two separate authority claims:

1. caller PATH must not choose the outer `env -i … dpkg` sanitizer in the candidate;
2. caller PATH must not choose the inner `dpkg` that receives chrootless execution options in the candidate.

The deliberate mutations must prove the opposite surfaces independently:

- inner mutation: fake caller-path `dpkg` receives `--force-script-chrootless`;
- outer mutation: fake caller-path `env` receives the sanitizer launch while inner `dpkg` remains canonical.

Flattened text can lose empty arguments, spaces, newlines, and exact option boundaries. That weakens the negative controls even when the package result itself is correct.

## Exact boundary

Owning issue: #337.

Canonical current-main candidate:

- PR #368;
- base/head at repair start: `c81d665e0acf9523e7f0d20247a8172a2a6648a3` / `6bc768e7c19f58f9984f87575c0114c7359e098d`;
- one-commit, eleven-file product/transaction carrier.

Repair construction branch:

- `repair/chrootless-direct-argv-receipt`;
- created directly from PR #368 head;
- changed surfaces: direct transaction, focused test, dedicated workflow, this record.

The imported mmdebstrap source and both retained product patches remain byte-identical to PR #368.

## Historical and adjacent precedent

Two earlier results establish the method:

1. LF-02 Run 25 showed that raw `$*` spilled package-script arguments into ambiguous whitespace tokens. Its accepted repair used `$@`, NUL delimiters, and production schema validation.
2. PR #367 repaired the apt-managed authority receipt with one NUL-delimited fake-`env` record per process and structural command classification.

The direct path should not retain weaker evidence than the apt path when both support one final authority decision.

## Record format

Both fake wrappers write:

```text
argv[0] NUL argv[1] NUL … argv[n] NUL
```

Each process writes one private file named with its PID.

Properties:

- `umask 077`;
- shell noclobber before file creation;
- trailing NUL required;
- empty arguments preserved;
- spaces, newlines, equals signs, and shell metacharacters preserved inside their original argument;
- receipt closed before delegation to `/usr/bin/env` or `/usr/bin/dpkg`.

The shared `tools/classify_env_argv.py` reader rejects symlink, nonregular, empty, and non-NUL-terminated files.

## Direct `env` classification

The direct transaction reuses the accepted apt classifier:

- `host-version-probe` — exact argv `--version`;
- `host-shell-hook` — parsed setup-hook shell form;
- `sanitizer-dpkg` — ignore-environment selected and command basename `dpkg`;
- `other-host` — every remaining valid caller-path invocation.

Direct Essential installation does not use a setup hook, so every direct case requires `host-shell-hook = 0`.

Expected direct `env` matrix:

| Variant | Version probe | Sanitizer | Setup hook |
| --- | ---: | ---: | ---: |
| candidate | at least 1 | 0 | 0 |
| inner mutation | at least 1 | 0 | 0 |
| outer mutation | at least 1 | at least 1 | 0 |

`other-host` remains retained evidence rather than being silently discarded.

## Direct `dpkg` classification

The fake caller-path `dpkg` wrapper writes the exact argv vector. The receipt requires:

- at least one vector exactly equal to `['--print-architecture']` in every case;
- zero vectors containing the exact element `--force-script-chrootless` for candidate and outer mutation;
- at least one such vector for the inner mutation.

A different argument such as:

```text
prefix--force-script-chrootless-suffix
```

is a negative control. It does not satisfy exact-element ownership.

## Combined per-case receipt

Every case retains:

- raw fake-`env` argv files;
- parsed env JSON;
- raw fake-`dpkg` argv files;
- parsed dpkg JSON;
- combined direct receipt JSON;
- classifier stdout and stderr;
- package stdout/stderr/status;
- installed package list;
- maintainer-script PATH result.

The combined receipt records:

```text
schema_version
env.host-version-probe
env.host-shell-hook
env.sanitizer-dpkg
env.other-host
dpkg.files_checked
dpkg.print-architecture
dpkg.force-script-chrootless
```

## Existing transaction contract preserved

The direct transaction still requires:

- candidate, inner mutation, and outer mutation all return 0;
- each reaches `run_essential()`;
- each installs `lf-essential-authority-probe`;
- candidate and outer mutation use canonical `/usr/sbin:/usr/bin:/sbin:/bin` inside the maintainer script;
- inner mutation uses the caller-controlled fake-bin prefix;
- all installed package sets are equal;
- imported source mode is unchanged;
- `git diff --exit-code -- upstream/mmdebstrap/mmdebstrap` passes;
- runtime cleanup remains below the existing validated disposable parent.

Only receipt serialization and classification change.

## Focused controls

`tests/test_direct_authority_argv_receipt.py` covers:

- exact dpkg argv vectors;
- exact-element versus substring distinction;
- env version/sanitizer/other-host distinction;
- explicit zero-record summaries;
- two lossless wrapper writes and no raw `$*`;
- required direct receipt JSON fields;
- JSON preservation of empty and newline-containing arguments.

The dedicated workflow compiles this test and the shared classifier before the full package transactions.

## Why this approach

### Why not keep the existing greps?

A grep over joined argv cannot prove where argument boundaries were. It can produce false positives on values and false negatives on quoting/whitespace.

### Why not reuse only the env classifier for dpkg?

The env parser owns GNU-style option and assignment prefixes. Fake `dpkg` evidence needs a simpler exact-vector record, not pretend env grammar.

### Why retain the architecture probe?

It is an expected caller-PATH `dpkg` use outside the inner sanitizer boundary. Retaining it proves that the fake wrapper was available and observed without confusing it with the chrootless package execution.

### Why not canonicalize every caller-path `dpkg` use?

That would broaden the product patch. The current decision concerns the `dpkg` launched inside the sanitized maintainer-script boundary. The architecture probe is host-side behavior and remains explicit evidence.

## Evidence boundary

This repair proves direct fixture argv identity and classification only.

It does not establish:

- every dpkg option spelling or response-file mechanism;
- every host-side `dpkg` use in mmdebstrap;
- executable replacement races after PATH lookup;
- all architectures or repository transports;
- every Essential package transaction;
- non-Debian filesystem layouts;
- upstream acceptance.

The product candidate remains a local retained patch composition against exact imported source.

## Cleanup and rerun

All raw and parsed receipts remain below the existing tracked result directory on the disposable runner. Runtime package and repository state remains below the validated temporary root and is removed through the existing EXIT cleanup.

No secret, live target, mount, external package repository, public issue, release, or deployment is involved.

## Stop rule

Stop this repair after:

1. focused exact-element controls pass;
2. the full direct Essential transaction passes all three variants;
3. raw and parsed env/dpkg receipts are uploaded;
4. repository and dedicated workflows pass on one exact head;
5. the repaired files are composed into PR #368 and the complete current-main carrier reruns.

Any broader host-side executable-authority policy belongs to a distinct source decision.

## Disposition

`REPAIR` until exact-head repository and dedicated transaction gates pass. A green unchanged head should merge into PR #368 and trigger one final current-main composition run.

## Authority

Internal Linux Fieldwork work only. No Debian or mmdebstrap upstream issue, email, patch, merge request, review, release, or deployment is included or authorized.
