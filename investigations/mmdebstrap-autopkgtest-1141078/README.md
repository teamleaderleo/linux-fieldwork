# mmdebstrap Debian sid autopkgtest reduction

Tracking: PR #72, issues #53, #54, #119, #153, and PR #171.

## TL;DR

Run `30578966104` completed 77 package-test cases, then failed at `(125/284) cwd-directory-not-accessible-by-unshared-user` because the reduction carrier exported relative `./mmdebstrap` and the test changed directories before execution.

The repaired carrier keeps the source-tree proxy for `coverage.sh` preflight, installs an executable copy at `$AUTOPKGTEST_TMP/mmdebstrap`, and exports that absolute path. A focused regression now executes the installation step, verifies byte and mode identity, changes cwd, and proves the temporary proxy—not a source-tree decoy—receives the hook arguments.

Next action: consume exact-head repository CI, then rerun the disposable Debian sid package test. Packet B remains unvalidated until its dedicated hook-free phase actually executes.

## Explain like I'm five

The test suite makes a tiny helper named `mmdebstrap`. Think of it as a forwarding telephone: calls to the helper are passed to the installed `/usr/bin/mmdebstrap` package.

One test walks into a different room before making the call. The old command said “use the helper in this room” (`./mmdebstrap`), so the helper disappeared when the room changed.

The first attempted repair wrote down the address `$AUTOPKGTEST_TMP/mmdebstrap` but forgot to put the helper there. The final repair does both: it copies the helper to that exact address and then uses the address after the directory change.

Literal example:

```text
source cwd: /tmp/autopkgtest.../real-tree
exported command: ./mmdebstrap --setup-hook=...
test action: env --chdir=/tmp/debian-chroot
old result: env: './mmdebstrap': No such file or directory
candidate: install proxy at /tmp/autopkgtest.../autopkgtest_tmp/mmdebstrap
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
- Failed run: `30578966104`
- Artifact: `mmdebstrap-reproduction-gha-30578966104-1`
- Artifact digest: `sha256:c1c691504e6606b914862d5457313071e9b7db5d38490b872e30b10bdfa741be`
- Console digest: `sha256:0ae1d172219b2a79c09d7e9b9534612434799d753e120979096e4da767452203`
- Candidate patch: `installed-command-wrapper.patch`
- New regression: `tests/test_mmdebstrap_autopkgtest_proxy_installation.py`

Imported source files remain unchanged; all patches apply to a disposable copy.

## Environment

The retained run used Debian sid inside the repository's disposable autopkgtest container. Its artifact records:

```text
AUTOPKGTEST_TMP=/tmp/autopkgtest.QVLAOw/autopkgtest_tmp
PWD=/tmp/autopkgtest.QVLAOw/build.AcG/real-tree
```

Those are different directories. That distinction exposed the incomplete first repair: exporting `$AUTOPKGTEST_TMP/mmdebstrap` is insufficient unless the proxy is installed there.

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

The patch now performs both required operations:

```sh
chmod 0755 ./mmdebstrap
install -m 0755 ./mmdebstrap "$AUTOPKGTEST_TMP/mmdebstrap"
```

and exports:

```text
$AUTOPKGTEST_TMP/mmdebstrap --setup-hook=... --hook-dir=...
```

The source-tree copy remains available for the historical `coverage.sh` source preflight. The installed temporary copy is the stable behavioral command and still forwards to `/usr/bin/mmdebstrap`.

The candidate deliberately does not use `$SRC/mmdebstrap`, rewrite the cwd-changing test, or claim that the proxy belongs in final reusable package tooling.

## Reproduction

Focused gate:

```sh
python3 -m unittest -v tests/test_mmdebstrap_autopkgtest_proxy_installation.py
```

The regression:

1. applies the exact retained patch to a temporary testsuite copy;
2. checks the complete patched testsuite with `/bin/sh -n`;
3. executes the exact `install -m 0755` line;
4. requires destination bytes and executable mode to match the generated proxy;
5. plants a source-tree decoy that exits `97`;
6. replaces the installed copy with an observable stand-in;
7. changes cwd and executes the rendered command;
8. requires the installed temporary path to receive both hook arguments.

The disposable sid rerun remains the authoritative package-level gate.

## Results

Demonstrated from run `30578966104`:

- the Deb822 compatibility candidate remained past its earlier failure;
- 77 broad-phase cases completed;
- `root-without-cap-sys-admin` was skipped out of the hook-heavy phase as intended;
- test 125 failed because the relative proxy vanished after `--chdir`;
- the dedicated hook-free phase never ran.

The first `$AUTOPKGTEST_TMP` repair was incomplete because patch text still created only `./mmdebstrap`. This was found by comparing the retained environment, patch action, exported command, and regression fixture rather than trusting the PR prose.

## Interpretation

**Demonstrated behavior:** a relative executable containing `/` is resolved after the cwd change and can disappear.

**Harness defect:** exporting an absolute path without creating the executable at that path is another pre-product failure.

**Design choice:** retain two investigation-only proxy copies—one source-tree copy for historical preflight and one temporary absolute copy for behavioral invocation.

**Open question:** after this repair, what is the first sid package-test result, and does the dedicated hook-free capability case execute with its hard-failure status contract?

## Evidence boundary

The focused regression uses temporary files and a stand-in executable. It proves path creation, byte/mode transfer, rendered argument selection, cwd independence, and decoy avoidance. It does not prove the installed Debian package, mirror, mount hooks, capability drop, or full package-test phase order.

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
