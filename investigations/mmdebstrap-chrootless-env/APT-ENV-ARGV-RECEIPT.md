# Lossless caller-path `env` receipts for apt-managed chrootless authority

## TL;DR

PR #349's product patches and package transactions reached the expected candidate, inner-mutation, and outer-mutation behaviors. Its dedicated run then failed because the fixture flattened every fake caller-path `env` invocation through `$*` and classified the result with substrings.

That receipt could not distinguish the governed chrootless `env -i … dpkg` sanitizer from host-side `env --version` and setup-hook launches that intentionally remain outside the two product patches.

This repair writes one NUL-delimited argv record per fake-`env` process, classifies command identity structurally, and requires only the product boundary:

- candidate and inner-path mutation: caller PATH must never own the dpkg sanitizer;
- outer-wrapper mutation: caller PATH must own at least one dpkg sanitizer launch;
- host version probes, setup hooks, and any other host calls remain retained evidence.

Both product patches and every package transaction command are unchanged.

## Explain like I'm five

The old notebook wrote every command argument as one sentence. A setup hook and a package sanitizer could then look alike because spaces erased where one argument ended and the next began.

The repaired notebook puts a separator between every argument and labels the actual command after reading the separators. It still records every other caller-path use instead of hiding it.

## Why care

The product question is narrow:

```text
Does caller PATH choose the env program that runs env -i … dpkg?
```

The source also uses ordinary host-side `env` for:

- a startup `env --version` dependency probe;
- setup-hook execution with `sh -c … exec TARGET`.

Those calls are separate authority surfaces. Treating every caller-path `env` invocation as a sanitizer failure makes a correct candidate look red. Ignoring every nonmatching line is also unsafe because it can hide a newly introduced caller-path sanitizer spelling.

Lossless argv and structural command parsing preserve both sides: the governed launch is authoritative, and outside-boundary host calls remain visible.

## Exact observed failure

Reviewed candidate:

- PR #349;
- exact head: `d7c464219920c9d8baeea3271988b61030b1c883`;
- repository CI: `30637439900` / 981, success;
- dedicated workflow: `30637426452` / 105, failure;
- artifact: `8795929587`;
- artifact ZIP SHA-256: `4261587c3e3c8bb0bce168d64ff7a8dae9e73c0f71754990ca372d33cc699503`.

The dedicated workflow passed:

- Perl and shell syntax;
- current Debian sid formatting;
- legacy environment-security regression;
- source-mode restoration and Git-state fence;
- the complete direct Essential-package transaction;
- candidate, clean, inner-mutation, and outer-mutation apt-managed package execution.

It then failed at the first receipt classifier:

```text
unexpected caller-path env invocation: candidate-tainted-outer-env.log
```

The exact first failure owner is evidence classification breadth. Neither retained product patch was rejected by that run.

## Source intent and adjacent call surfaces

The imported source's `can_execute()` checks required tools by executing each with `--version`; `env` is in that required-tool list.

The setup-hook runner also invokes bare `env` with normalized environment options, then executes either a direct hook or:

```text
env [options] sh -c SCRIPT exec TARGET
```

The apt transaction deliberately uses `--setup-hook` to copy its local package into the target. A tainted caller PATH therefore records at least:

- one exact `--version` call;
- one host shell-hook call.

Patch 0002 changes only the two chrootless dpkg sanitizer launch surfaces to validated `/usr/bin/env`. It does not claim to canonicalize every host-side `env` use in mmdebstrap.

## Repair boundary

Construction branch:

- `repair/chrootless-env-authority-argv-receipt`;
- exact parent: PR #349 head `d7c464219920c9d8baeea3271988b61030b1c883`.

Changed surfaces:

- `tools/classify_env_argv.py`;
- `tests/test_classify_env_argv.py`;
- `investigations/mmdebstrap-chrootless-env/apt_authority_transaction.sh`;
- `.github/workflows/mmdebstrap-chrootless-env-security.yml`;
- this record.

No imported source, product patch, direct transaction, package fixture payload, or external interaction changes.

## Lossless record format

The fake caller-path `env` wrapper creates a private file named with its process ID and writes:

```text
argv[0] NUL argv[1] NUL … argv[n] NUL
```

Properties:

- `umask 077` protects the local receipt;
- shell noclobber rejects a repeated record identity instead of overwriting evidence;
- empty arguments remain distinguishable;
- spaces, newlines, equals signs, and shell metacharacters remain inside their original argument;
- the wrapper closes the receipt before delegating to `/usr/bin/env`.

The classifier rejects symlink, nonregular, empty, and non-NUL-terminated records.

## Structural classification

`tools/classify_env_argv.py` parses the `env` option/assignment prefix and retains one of four classes:

### `host-version-probe`

Exact argv:

```text
--version
```

### `host-shell-hook`

The command after recognized `env` options/assignments is `sh`, followed by:

```text
-c SCRIPT exec TARGET
```

The script body is evidence only. Merely containing the word `dpkg` does not make the record a sanitizer.

### `sanitizer-dpkg`

The parsed invocation includes `-i` or `--ignore-environment`, and the selected command basename is `dpkg`.

This is the authority boundary owned by patch 0002.

### `other-host`

Every remaining valid caller-path invocation. These records are retained in the JSON receipt and count summary. They do not silently pass as sanitizer use and are not discarded.

`env -S` / `--split-string` remains `other-host` because it introduces a second parser layer. The classifier does not guess command identity across that boundary.

## Transaction contract

For tainted caller PATH:

| Variant | Version probe | Setup hook | Caller-path dpkg sanitizer |
| --- | ---: | ---: | ---: |
| candidate | at least 1 | at least 1 | exactly 0 |
| inner PATH mutation | at least 1 | at least 1 | exactly 0 |
| outer wrapper mutation | at least 1 | at least 1 | at least 1 |

For clean caller PATH, explicit configured inner path, and empty configured path:

- fake caller-path `env` must not execute at all;
- the receipt is an explicit zero-record JSON summary.

The transaction still separately requires:

- successful package installation for all success variants;
- candidate/clean PATH equality;
- inner mutation executing the fake inner helper;
- outer mutation not executing the inner helper;
- explicit non-empty `DPkg::Path` authority;
- empty configured path failing before maintainer-script execution;
- equal installed package sets;
- unchanged imported source mode and Git diff.

## Focused controls

`tests/test_classify_env_argv.py` covers:

- round-trip of spaces, newlines, empty strings, and equals signs;
- exact version-probe classification;
- sanitizer requiring both ignore-environment and a structurally selected `dpkg` command;
- host setup-hook classification from argv shape;
- a hook script mentioning `dpkg` remaining a hook, not a sanitizer;
- all four classes in one directory receipt;
- explicit empty-directory receipt;
- missing trailing NUL and symlink rejection;
- transaction source requiring lossless records and JSON classification;
- removal of raw `$*` and substring sanitizer assertions;
- retention of `other-host` evidence.

The dedicated workflow compiles the classifier and focused test before running the real package transactions.

## Why this approach

### Why not quote `$@` into a text line?

Shell quoting is a serialization format only when the encoder and decoder are exact and shared. Raw or ad hoc quoting still risks ambiguity around empty strings, newlines, and implementation-specific escapes.

### Why not allowlist one extra raw line?

The observed setup-hook argv depends on environment options and the hook script. A literal line allowlist would be another formatting receipt rather than command-identity evidence.

### Why not fail on every `other-host` call?

That would silently broaden patch 0002 from “canonicalize the dpkg sanitizer” to “canonicalize every host-side `env` call.” The current source and candidate do not make that claim. Unknown host calls remain visible for a separate source decision.

### Why not ignore all host calls?

The outer mutation must prove that a caller-path sanitizer is actually observable. Structural parsing keeps that negative control authoritative.

## Evidence boundary

This repair proves argv identity and receipt classification for the transaction fixture.

It does not prove:

- that every host-side bare `env` use is desirable;
- all GNU/BSD `env` option grammar;
- `env -S` second-layer command identity;
- executable replacement races after PATH lookup;
- every apt/dpkg invocation shape;
- every architecture, credential, proxy, TMPDIR, or fakeroot combination;
- upstream acceptance.

Host-side setup-hook and dependency-probe authority remain explicit future questions, not hidden failures.

## Cleanup and rerun

The transaction keeps all runtime state below its validated disposable runtime parent and removes it through the existing EXIT cleanup. Receipt files live under the tracked result directory uploaded by the disposable hosted runner.

The repair introduces no persistent process, mount, socket, package repository, credential, or public target. Fresh exact-head repository and dedicated workflow execution remain authoritative.

## Disposition

`REPAIR` until:

1. exact-head repository CI passes the focused classifier matrix;
2. the dedicated workflow passes all direct and apt-managed transactions;
3. the artifact retains each per-case JSON receipt and raw argv directory;
4. complete five-file review confirms both product patches are unchanged.

A green unchanged head should advance the PR #349 composition to final cross-context review.

## Authority

Internal Linux Fieldwork work only. No Debian, mmdebstrap upstream, external issue, email, release, deployment, or other public contact is included or authorized.
