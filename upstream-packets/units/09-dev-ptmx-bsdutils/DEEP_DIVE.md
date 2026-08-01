# Deep dive

## Mechanism

`tests/dev-ptmx` uses host-side `script -qfec` to provide a pseudo-terminal, then invokes `script(1)` twice inside the generated root:

1. root: `chroot "$1" script -c "echo foobar"`;
2. generated user: `chroot "$1" runuser -u user -- env --chdir=/home/user script -c "echo foobar"`.

The two inner calls depend on the root's package selection. Historical baseline:

```text
gcc,libc6-dev,python3,passwd
```

`bsdutils` provides `/usr/bin/script`. Once Debian stopped supplying it through the former Essential-set assumption, recovered CI run `72574145` failed before the intended PTY assertions completed.

## Correct ownership

The dependency belongs in the generated-root `--include` declaration:

- host-side availability was already present;
- mmdebstrap runtime does not generally require `script`;
- util-linux packaging should not be changed to accommodate one test fixture;
- replacing `script` would change test intent.

## Linux Fieldwork candidate

The controlled downstream candidate changed one line and preserved all hooks:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=bsdutils,gcc,libc6-dev,python3,passwd \
```

It applied to exact baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` and produced blob `fa93b4b845ff4927a72f258364bd920e8c7dc573`. Static validation and two current-sid executions passed.

## Why the GitHub fork looked current but was incomplete

`teamleaderleo/mmdebstrap` follows `deepin-community/mmdebstrap` at downstream import commit `574048f2a720057b75e56622003932f344dc700a`. The source bytes match Debian `1.5.7-3`, making it a valid package-execution carrier. Its ancestry does not include later canonical Forgejo `develop` work.

A newer timestamp on another GitHub fork likewise represented local divergence, not canonical freshness. Branch and commit ancestry matter more than repository name or update date.

## Canonical audit method

Local DNS could not reach Forgejo or Salsa, so internal PR `#411` used a networked GitHub Actions runner for a read-only audit:

- mirror-cloned canonical Forgejo and Debian Salsa repositories;
- recorded all advertised refs;
- extracted exact `main` bytes and blob identity;
- inspected full `tests/dev-ptmx` history with patches;
- searched every ref's content;
- ran pickaxe and regex history searches;
- captured public Forgejo issue/PR, Debian BTS, and mailing-list search responses;
- uploaded 42 receipt files.

Audit identity:

```text
run: 30704384974
job: 91380861751
artifact: 8819850852
digest: sha256:0504ab41ec727ffb87c5f803a6dc0611534ce0df0c0eadc2587a998808de9c2b
```

## Canonical branch distinction

Canonical stable head:

```text
main: 77ec9be5417ee44c96343d2347145585da1b1f94
tests/dev-ptmx blob: ca1cde040f945fe871f904ef6a56e040b6a5c9ea
include: gcc,libc6-dev,python3,passwd
```

Canonical development head:

```text
develop: 6e1e572bc49456daab7fd1274b1f3b8ec4a1c248
include: gcc,libc6-dev,python3,passwd,bsdutils
corrected blob: 258a7f9579b2a2b91b6758952851296b44197ae0
```

The correction is also reachable from tag `1.5.7+develop`.

## Canonical owning commit

```text
commit: c75b58e3c88b1f49626b9ee073e9e9688d38922c
parent: 6de6403eca9d606a88ce8f6eb0bba097d9f7369e
author date: 2025-11-16T00:04:44+01:00
subject: make_mirror.sh,tests/dev-ptmx: explicitly install bsdutils for script utility
```

Canonical hunk:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=gcc,libc6-dev,python3,passwd,bsdutils \
```

The package set matches Linux Fieldwork's candidate. Canonical ordering appends `bsdutils`; canonical source owns the final form.

## Classifier correction

The audit's generated summary initially said the corrected include was absent from history. That field searched only the exact Linux Fieldwork ordering `bsdutils,gcc,...`. Full path history found canonical's appended ordering.

The tracker and mailing-list regex also counted unrelated substring matches, including `pty` inside other words. Exact Git history is the decisive overlap evidence.

## Final disposition

Unit 09 is `RETIRED` because the correction already exists in canonical development history. The historical failure, regressions, downstream candidate, and current-sid double pass remain useful validation of the existing upstream change. No competing external submission is appropriate.
