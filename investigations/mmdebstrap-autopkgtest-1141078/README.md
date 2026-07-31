# mmdebstrap Debian sid autopkgtest reduction

Tracking: PR #72, issues #53, #54, #119, #153, and PR #171.

## TL;DR

Run `30578966104` completed 77 package-test cases, then failed at `(125/284) cwd-directory-not-accessible-by-unshared-user` because the reduction carrier exported relative `./mmdebstrap` and the test changed directories before execution.

Run `30584581782` then exposed a second harness defect before any package case: the testsuite had already changed into `$AUTOPKGTEST_TMP`, so `./mmdebstrap` and `$AUTOPKGTEST_TMP/mmdebstrap` were the same file. The added `install` command rejected that self-copy.

The repaired carrier creates and marks the proxy executable in `$AUTOPKGTEST_TMP`, then exports that existing file's absolute path. A focused regression models the same cwd, changes directories for execution, and proves the temporary proxy—not a source-tree decoy—receives the hook arguments. PR #72 carries the moving exact head and gate receipt.

Next action: consume exact-head repository CI, then rerun the disposable Debian sid package test. Packet B remains unvalidated until its dedicated hook-free phase actually executes.

## Explain like I'm five

The test suite makes a tiny helper named `mmdebstrap`. Think of it as a forwarding telephone: calls to the helper are passed to the installed `/usr/bin/mmdebstrap` package.

One test walks into a different room before making the call. The old command said “use the helper in this room” (`./mmdebstrap`), so the helper disappeared when the room changed.

The testsuite already builds the helper inside `$AUTOPKGTEST_TMP`. The broken repair tried to copy the helper onto itself. The current repair marks that existing helper executable and uses its absolute address after the directory change.

Literal example:

```text
proxy cwd: /tmp/autopkgtest.../autopkgtest_tmp
exported command: ./mmdebstrap --setup-hook=...
test action: env --chdir=/tmp/debian-chroot
old result: env: './mmdebstrap': No such file or directory
failed repair: install proxy onto that same proxy → "are the same file"
candidate: use /tmp/autopkgtest.../autopkgtest_tmp/mmdebstrap directly
candidate result: that proxy runs and receives both hook arguments
```

## Why care

A harness failure can impersonate a package failure. Here it also blocked the exact `root-without-cap-sys-admin` scheduling question owned by Packet B.

A tempting alternative, `$SRC/mmdebstrap`, survives the directory change but executes the imported source script. That would silently change the subject from the installed Debian package to the checkout and produce a convincing answer to the wrong question.

## Intent and precedent

The imported cwd-changing test intentionally canonicalizes the two recognized relative source commands before invoking `env --chdir`. The reduction carrier added hook arguments to `./mmdebstrap`, so the exact-string safeguard no longer matched.

The stable design rule is to choose executable identity before changing directories:

- GNU `env --chdir=DIR` changes directory before invoking the command: https://www.gnu.org/software/coreutils/manual/html_node/env-invocation.html
- Rust warns that relative program paths combined with `Command::current_dir` are platform-specific and recommends canonicalizing the program path: https://doc.rust-lang.org/std/process/struct.Command.html#method.current_dir
- systemd service commands use an absolute path or a simple executable name searched in a fixed path; relative paths containing `/` are not the contract: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html

These are precedent for the design choice, not evidence that upstream intended this temporary proxy mechanism.

## Question

Can the investigation-only installed-package proxy remain executable after a test changes cwd, without accidentally executing the imported source script?

## Source

- Project: Debian `mmdebstrap` package test reduction
- Imported package boundary: `mmdebstrap 1.5.7-3`
- Imported source path: `upstream/mmdebstrap`
- Broad carrier: PR #72
- Focused scheduling candidate: PR #171
- Failed carrier head: `ff89c85712ebcd888cba15ebb803bf7f7134c032`
- Semantic repair commit: `7d78cf6d67a2b1b1c1e8fe409cab93bb36b408bd`
- Failed run: `30578966104`
- Artifact: `mmdebstrap-reproduction-gha-30578966104-1`
- Artifact digest: `sha256:c1c691504e6606b914862d5457313071e9b7db5d38490b872e30b10bdfa741be`
- Console digest: `sha256:0ae1d172219b2a79c09d7e9b9534612434799d753e120979096e4da767452203`
- Candidate patch: `installed-command-wrapper.patch`
- Run 653 artifact: `8777645645`
- Run 653 artifact digest: `sha256:e7b0ed6131a18fa083e7e7d513d6df5ffff6414dde741785463ea9dffd1504af`
- Regression: `tests/test_mmdebstrap_autopkgtest_proxy_installation.py`

Imported source files remain unchanged; all patches apply to a disposable copy.

## Environment

Run 653 used Debian sid inside the repository's disposable autopkgtest container. Its trace records:

```text
AUTOPKGTEST_TMP=/tmp/autopkgtest.KTDBkM/autopkgtest_tmp
SRC=/tmp/autopkgtest.KTDBkM/build.pNo/real-tree
PWD at proxy creation=/tmp/autopkgtest.KTDBkM/autopkgtest_tmp
```

`SRC` and `AUTOPKGTEST_TMP` are different directories, but the proxy is created only after the testsuite changes into `AUTOPKGTEST_TMP`. Therefore `./mmdebstrap` already names `$AUTOPKGTEST_TMP/mmdebstrap`.

## Baseline behavior

The retained run passed 77 cases and then rendered this command:

```text
env --chdir=/tmp/debian-chroot ./mmdebstrap --setup-hook=... --hook-dir=...
```

The observed result was:

```text
env: './mmdebstrap': No such file or directory
test.sh failed
```

The broad phase used `--exitfirst`, so the later dedicated hook-free phase did not execute. This artifact neither validates nor refutes Packet B runtime behavior.

## Candidate

The patch creates the proxy in the current `$AUTOPKGTEST_TMP` directory and marks it executable:

```sh
chmod 0755 ./mmdebstrap
```

and exports:

```text
$AUTOPKGTEST_TMP/mmdebstrap --setup-hook=... --hook-dir=...
```

The same temporary proxy remains the historical `coverage.sh` preflight subject and the stable behavioral command. It forwards behavioral invocations to `/usr/bin/mmdebstrap`.

The candidate deliberately does not use `$SRC/mmdebstrap`, rewrite the cwd-changing test, or claim that the proxy belongs in final reusable package tooling.

## Reproduction

Focused gate:

```sh
python3 -m unittest -v tests/test_mmdebstrap_autopkgtest_proxy_installation.py
```

The regression:

1. applies the exact retained patch to a temporary testsuite copy;
2. checks the complete patched testsuite with `/bin/sh -n`;
3. rejects the self-copying `install` command and requires the executable-mode command;
4. creates the generated proxy at the exact product cwd and exported absolute path;
5. plants a source-tree decoy that exits `97`;
6. replaces the temporary proxy with an observable stand-in;
7. changes cwd and executes the rendered command;
8. requires the existing temporary path to receive both hook arguments.

The disposable sid rerun remains the authoritative package-level gate.

## Results

Demonstrated from run `30578966104`:

- the Deb822 compatibility candidate remained past its earlier failure;
- 77 broad-phase cases completed;
- `root-without-cap-sys-admin` was skipped out of the hook-heavy phase as intended;
- test 125 failed because the relative proxy vanished after `--chdir`;
- the dedicated hook-free phase never ran.

The first review assumed `./mmdebstrap` was created outside `$AUTOPKGTEST_TMP` and added an installation copy. Run 653's exact shell trace disproved that assumption: the testsuite changes into `$AUTOPKGTEST_TMP` before creating the proxy.

Run `30584581782` proved the absolute path existed, but the added installation command executed after `cd "$AUTOPKGTEST_TMP"` and failed:

```text
install: './mmdebstrap' and '/tmp/autopkgtest.KTDBkM/autopkgtest_tmp/mmdebstrap' are the same file
```

The failure occurred before the numbered package-test matrix. Artifact `8777645645` retained 25 files and digest `sha256:e7b0ed6131a18fa083e7e7d513d6df5ffff6414dde741785463ea9dffd1504af`.

## Interpretation

**Demonstrated behavior:** a relative executable containing `/` is resolved after the cwd change and can disappear.

**Harness defect:** copying the proxy onto its own absolute identity is another pre-product failure.

**Design choice:** use the single investigation-only proxy already created in `$AUTOPKGTEST_TMP`; export its absolute identity for cwd-changing behavioral invocations.

**Open question:** after this repair, what is the first sid package-test result, and does the dedicated hook-free capability case execute with its hard-failure status contract?

## Evidence boundary

The focused regression uses temporary files and a stand-in executable. It proves product-cwd identity, rendered argument selection, cwd independence, and decoy avoidance. It does not prove the installed Debian package, mirror, mount hooks, capability drop, or full package-test phase order.

The broad carrier remains an investigation mechanism. Final reusable package tooling should remove the proxy and prove the installed package through the original preflight path. An earlier ordinary broad-phase failure may still starve the dedicated Packet B phase under `--exitfirst`.

## Next step

The reviewer is choosing whether the corrected proxy installation is sufficient to justify another disposable sid run. Supporting evidence must include:

- exact-head repository CI with the new regression;
- complete current diff review;
- a fresh artifact showing which program path ran;
- the first named test result;
- whether the dedicated Packet B phase executed;
- cleanup, status, and artifact identity.

If an unrelated broad failure appears first again, the investigation carrier should consider deferring that ordinary status, running the focused phase, then restoring the deferred failure. Such ordering must remain investigation-only and must never turn a real package failure into success.

## Authority

Internal Linux Fieldwork work only. No Debian or other external issue, email, patch, merge request, comment, or review is authorized or included.
