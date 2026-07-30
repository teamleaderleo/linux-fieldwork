# Restore Nixpkgs gomarkdoc checks

Tracking: issue #136 and the LF-35 package-candidate lane.

## TL;DR

Nixpkgs currently builds `gomarkdoc` 1.1.0 with its Go test suite disabled. This investigation runs the real package against a reported good revision, a reported bad revision, and a pinned current revision. It compares five narrow test environments without changing the installed binary or weakening shared Go vendoring.

The initial source review found two independent facts:

1. newer `buildGoModule` places its generated `GOFLAGS` in the derivation environment, so gomarkdoc's own in-process parser sees Nixpkgs' `-mod=vendor`;
2. gomarkdoc's tests explicitly request `../.gomarkdoc-empty.yml`, but that file is absent from the v1.1.0 source tag and current repository.

Neither fact is called the root cause until the hosted matrix distinguishes them.

## Explain like I'm five

Nixpkgs is the factory. Gomarkdoc is a tool being inspected before shipment.

The factory puts a note in the environment:

```text
GOFLAGS=-mod=vendor -trimpath
```

The note is meant for the Go compiler. Gomarkdoc also reads the note, but its tiny parser understands only `-tags`. It complains about the factory's instructions as though they were gomarkdoc command-line options.

The test suite also asks for an empty instruction card:

```text
../.gomarkdoc-empty.yml
```

That card is not included in the released source box.

The package currently solves this by skipping inspection entirely:

```nix
doCheck = false;
```

The matrix asks whether we can put the correct card on the test bench, remove only factory-private flags from the test process, or do both—while preserving legitimate Go build tags and leaving the actual product build unchanged.

## Why care

With `doCheck = false`, Nixpkgs verifies that the binary compiles and reports a version, but it does not run gomarkdoc's bundled behavior tests. A future package or dependency change can therefore break documentation generation, config handling, output comparison, tags, nested packages, or embedding without the package build noticing.

A broad `buildGoModule` change would be risky because thousands of Go packages rely on its vendoring and reproducibility flags. The first candidate must be package-local unless another package proves the shared abstraction is wrong.

## Intent and precedent

### Nixpkgs intent

`buildGoModule` deliberately adds `-mod=vendor` so builds use the fixed vendored dependency tree and adds `-trimpath` for reproducibility. Its check phase already removes `-trimpath` because tests may inspect source paths. Moving `GOFLAGS` into `env` was part of structured-attribute support, not a gomarkdoc-specific behavior change.

Relevant Nixpkgs commits:

- `44876c60042bfb0be160a3104b53a3fe7bfc3969` moved build environment variables into `env` while explicitly leaving `GOFLAGS` for later;
- `83549e3ad2816a4ac1fd94de654b0590bf634dda` / `caff8c21cd2f5266e82bcb32269fa3235d995bf8` moved the computed `GOFLAGS` string into that environment.

### Gomarkdoc intent

`defaultTags()` deliberately reads `GOFLAGS` to inherit Go build tags. Its private parser accepts only `-tags`; a parse error prints a diagnostic and returns no tags.

The v1.1.0 tests also mutate process-wide `GOFLAGS`, working directory, arguments, and Viper configuration while calling `main()` in-process. Those choices make the suite sensitive to inherited and retained process state.

### Interpretation

The vendoring flag and tag inheritance are individually intentional. Their collision is accidental. The missing empty config fixture is a separate source/test packaging defect. The matrix determines which one actually changes the package result.

## Exact source boundary

- Nixpkgs issue: `NixOS/nixpkgs#516481`;
- reported good revision: `4590696c8693fea477850fe379a01544293ca4e2`;
- reported bad revision: `acd02b8771d0546f96ee281ac45c3a6f81b9bfba`;
- pinned current revision: `396e6226eab2fd092b1690abcd33ea522fde16dc`;
- package: `pkgs/by-name/go/gomarkdoc/package.nix`;
- shared builder: `pkgs/build-support/go/module.nix`;
- upstream source: `princjef/gomarkdoc@v1.1.0`;
- upstream tests: `cmd/gomarkdoc/command_test.go`;
- upstream parser: `cmd/gomarkdoc/command.go`.

A live overlap refresh on 2026-07-31 found the issue still open with no comments and no open Nixpkgs pull request matching `gomarkdoc`. Promotion remains internal; no upstream contact is authorized.

## Matrix

Each revision runs the same five modes:

| Mode | Build behavior | Test-only change |
|---|---|---|
| `baseline` | unchanged | none |
| `unset-goflags` | unchanged | remove inherited `GOFLAGS` before tests as a broad differential control |
| `filter-goflags` | unchanged | retain only supported `-tags` spellings before tests |
| `add-fixture` | unchanged | create the referenced empty config file |
| `add-fixture-filter-goflags` | unchanged | create the fixture and retain only supported tag flags |

`matrix.nix` uses `overrideAttrs` to set `doCheck = true`. Fixture creation happens in `postPatch`; flag changes happen in `preCheck`. Dependency vendoring, compilation, linker flags, source, installed output, and package metadata remain unchanged.

The combined mode intentionally uses tag filtering rather than complete flag removal. It therefore tests the bounded correction we could actually recommend while `unset-goflags` remains available to show whether a broader workaround changes the result.

`run_matrix.py` records for every case:

- exact Nixpkgs revision and mode;
- exit status and duration;
- timeout state;
- full Nix build log;
- counts for unsupported `-mod`, unsupported `-other`, missing config, package failure, and Go test `PASS` text.

It requires the reported good baseline to pass, the reported bad baseline to fail, and every case to finish within its bound. Symptoms never substitute for exit status.

## Distinguishing outcomes

### Test-time flags are sufficient

`unset-goflags` or `filter-goflags` passes while `add-fixture` fails.

Interpretation: inherited Nixpkgs builder flags are the package regression. Prefer a package-local `preCheck` that preserves only supported tags. Do not weaken shared vendoring.

### Missing fixture is sufficient

`add-fixture` passes while flag-only modes fail.

Interpretation: restore the explicit empty fixture in the package source during tests, or carry an upstream test patch after authorization.

### Both interact

Only `add-fixture-filter-goflags` passes.

Interpretation: the package needs the missing test fixture plus a package-local filter that preserves gomarkdoc's supported `-tags` contract while excluding builder-private flags.

### Baseline now passes

Current `baseline` passes.

Interpretation: the candidate has expired. Remove `doCheck = false` only after verifying current package source and test identity; otherwise close with a stale-report result.

### Nothing passes

Retain the logs and inspect Go version, Viper global state, package selection, and generated output differences. Do not guess or clear broader environment state.

## Reproduction

Hosted execution is the supported path because it installs Nix in a disposable GitHub runner and retains all logs:

```sh
python3 -m unittest tests.test_gomarkdoc_test_restoration -v
python3 investigations/gomarkdoc-test-restoration/run_matrix.py \
  --results "$PWD/evidence/gomarkdoc-manual"
```

The results directory must not already exist. This prevents a new run from silently mixing evidence with an older run.

## Evidence boundary

The matrix proves package behavior on Linux x86-64 with the Nix version installed by the pinned workflow action and the three exact Nixpkgs revisions. It does not prove behavior on Darwin, other architectures, another Go version, or unreleased gomarkdoc source.

Creating the absent fixture in `postPatch` proves whether its presence changes the suite; it does not establish what content upstream intended beyond the filename's explicit “empty” contract.

Filtering or clearing test-time `GOFLAGS` is package-local. It does not establish that shared `buildGoModule` should stop exporting flags, nor that arbitrary Go programs should ignore inherited `GOFLAGS`. Complete removal is a differential control; tag-only filtering is the bounded candidate.

## Current decision

Disposition: `INVESTIGATE` until the exact-head hosted matrix completes.

The reviewer will choose among a package-local tag filter, a fixture restoration, a split correction, a shared-builder follow-up supported by additional packages, or closure with a negative/stale result.

## Authority

Internal Linux Fieldwork investigation only. Reading public Nixpkgs and gomarkdoc source is authorized. No issue comment, pull request, review, patch submission, email, or other external contact is included or authorized.
