# Deep dive

## Question and observed failure

Can the Debian mmdebstrap package test run its intended current-sid matrix without failing in compatibility setup, carrier command lookup, signal syntax, or cross-phase fixture reuse?

The carrier sequence exposed six distinct blockers in order:

1. `debian/tests/sourcesfilter` rejected a real `Deb822SourceEntry` before package behavior ran.
2. A relative installed-command proxy disappeared after a test changed directory.
3. procps `/bin/kill --signal INT -- -PGID` rejected the negative process-group target.
4. `root-without-cap-sys-admin` dropped `CAP_SYS_ADMIN`, then a global file-mirror hook attempted `mount --bind` and failed before the mmdebstrap assertion path.
5. Moving the consumer to a hook-free phase exposed its hidden `tar1.txt` prerequisite.
6. Marking `create-directory` hook-free-only left the broad phase with a stale baseline generated without host APT hooks.

The first five failures prevented intended test execution. The sixth proved a shared fixture belonged to each execution phase.

## Source mechanism

### Deb822 source handling

`SourcesList(False, deb822=True)` returns raw Deb822 paragraphs. Exploded entries proxy their parent `file` attribute through a read-only property. The correction roots each raw entry's file path first, then iterates `sources.exploded_list()` so existing filtering, component reduction, URI rewriting, duplicate removal, and save behavior operate on single-value entries.

### Installed command identity

`coverage.py` substitutes `CMD` directly into generated shell tests. Tests such as `cwd-directory-not-accessible-by-unshared-user` execute after changing directory. The package suite should name the installed binary independently of the working directory. The distilled correction uses `/usr/bin/mmdebstrap` in the broad package invocation and discards the LF formatted proxy.

### Process-group SIGINT

The test computes a negative process-group ID. Current sid procps rejected the external long `--signal` spelling with that target. The dedicated topology probe established two status-zero whole-group candidates in its exact environment: dash builtin `kill -s INT -- -PGID` and external compact `/bin/kill -INT -- -PGID`. The retained correction uses dash explicitly so shell choice stays controlled.

### Hook-free hard consumer

The capability test deliberately removes `CAP_SYS_ADMIN`. Host APT setup attaches mount-dependent hooks, creating a circular fixture requirement. `Needs-Hook-Free-APT-Config` lets `coverage.py` skip the consumer during host-hook execution and schedules it later with plain `CMD=mmdebstrap`. Ordinary child failures stay authoritative; only GNU timeout status 124 maps to 77.

### Phase-local archive baseline

`tests/create-directory` writes `tar1.txt`. `tests/root-without-cap-sys-admin` reads that file after creating its archive. The broad suite has additional consumers such as `unshare-as-root-user`. Therefore fixture ownership is:

- focused hook-free phase: explicit `create-directory` prefix, then the capability consumer;
- broad host-hook phase: ordinary `create-directory` execution, regenerating `tar1.txt` under host hooks before broad consumers.

Only the consumer carries hook-free metadata. Global producer classification would suppress broad regeneration.

## Reproduction narrative

The historical real-sid runs form one progressive reproduction:

- Run 692 exposed the Deb822 assertion.
- Run 939 reached the capability case and failed because `tar1.txt` was absent after mmdebstrap completed.
- Run 974 passed the focused producer and capability consumer, then failed a broad consumer against the stale hook-free baseline.
- Run 999 passed the focused producer/consumer and later broad producer, completed 154 tests, and reached the independent `chrootless` directory-mtime result.

Detailed commands and artifact identities are in `TESTS.md`.

## Approach history

### Approach A — reject Deb822 and keep one-line-only behavior

- Mechanism: retain the `Deb822SourceEntry` assertion.
- Result: current sid source configuration fails before package behavior.
- Disposition: rejected.

### Approach B — explode first, then assign each exploded file

- Mechanism: call `exploded_list()` and write the proxied `file` property.
- Result: incompatible with read-only proxy behavior.
- Disposition: rejected.

### Approach C — root raw files, then explode

- Mechanism: mutate raw `sources.list` file paths first, then iterate exploded entries.
- Result: passed real package execution.
- Disposition: selected.

### Approach D — formatted relative installed-command proxy

- Mechanism: replace the fake preflight file with a Perl proxy to `/usr/bin/mmdebstrap` and use it as `CMD`.
- Result: behavioral execution reached the installed package, while `env --chdir` lost the relative proxy; it also weakened the source/preflight distinction.
- Disposition: rejected for upstream delivery; useful carrier evidence only.

### Approach E — absolute temporary proxy

- Mechanism: use `$AUTOPKGTEST_TMP/mmdebstrap`.
- Result: cleared directory changes in the disposable carrier.
- Compatibility cost: package behavior remained coupled to LF proxy machinery.
- Disposition: distilled to direct `/usr/bin/mmdebstrap` selection.

### Approach F — external procps long signal spelling

- Mechanism: `/bin/kill --signal INT -- -PGID`.
- Result: parser/target rejection on current sid.
- Disposition: rejected for the current package test.

### Approach G — status-zero whole-group spelling

- Mechanism: `/bin/dash -c 'kill -s INT -- "$1"' dash "$pgid"`.
- Result: whole-group delivery, zero command status, unrelated-process containment in the sid probe; subsequent package carrier advanced.
- Disposition: selected with current-sid/Linux boundary.

### Approach H — move capability case into the soft skipped phase

- Mechanism: execute without host hooks but map every failure to 77.
- Result: fixture compatibility improved while actual product failure lost authority.
- Disposition: rejected.

### Approach I — mark producer and consumer hook-free-only

- Mechanism: metadata selects both tests.
- Result: focused pair passed; broad phase skipped the producer and reused a baseline from a different hook configuration.
- Disposition: superseded.

### Approach J — consumer-only metadata plus explicit producer prefix

- Mechanism: select the consumer through metadata, fail closed on an empty class, prepend `create-directory`, run both in one hard invocation, then let broad coverage execute the producer again.
- Result: run 999 cleared focused and broad fixture identities.
- Disposition: selected.

## Selected correction

The ordered four-patch series contains only upstream package-test source changes. It removes every mechanism whose purpose was LF evidence collection or disposable-carrier adaptation.

## Why the changes belong together

They are sequential blockers in one Debian autopkgtest entry point and were validated through one progressive sid execution. Each patch stays independently reviewable, while the final claim depends on their composition: the package suite reaches the next unrelated test result.

## Compatibility analysis

- **Source formats:** Deb822 multi-value paragraphs become individual mutable entries; one-line entries retain existing filtering.
- **Command lookup:** broad execution binds to Debian's installed path `/usr/bin/mmdebstrap` and ceases to depend on `PATH` or working directory.
- **Signals:** the selected spelling is tied to dash and current sid/Linux process-group behavior.
- **Statuses:** signal command status must be zero; capability child statuses remain hard; timeout 124 becomes 77.
- **Fixtures:** `tar1.txt` is regenerated once per applicable execution phase. `pkglist.txt` is outside the capability dependency.
- **Hooks and mounts:** the capability pair runs without `sourcesfilter` and file-mirror automount hooks; broad tests retain them.
- **Cleanup:** historical disposable containers exited and artifacts uploaded; no persistent mounts or package state survived hosted runs.

## Unresolved questions

1. Does the four-patch series apply with zero fuzz and zero offset to current Salsa `master`?
2. Has Salsa `master` already adopted any equivalent Deb822, command-path, signal, or scheduling change?
3. Does the direct `/usr/bin/mmdebstrap` hunk pass upstream-native source/preflight expectations without the LF proxy?
4. Should maintainers review this as one merge request with four commits or as a short ordered MR series?

## Evidence boundary

Historical hosted runs prove the carrier generations named in `TESTS.md`. They do not prove the newly distilled exact series head. The first incomplete technical gate is a fresh checkout, exact series application, focused syntax/tests, cleanup, rerun, and current-sid package execution without LF-only machinery.
