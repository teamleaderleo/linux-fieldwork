# Project instructions and gate map

Reviewed: `2026-08-01`  
Unit: issue #397, unit 19  
External contact authorized: `false`

## Instruction files reviewed

| File | Imported blob | Relevant instruction |
| --- | --- | --- |
| `upstream/mmdebstrap/README.md` | `281e551bdf4af6e8336dca8a93cdf278a6be4cab` | Build the local mirror with `./make_mirror.sh`; run the suite with `CMD=./mmdebstrap ./coverage.sh`; named tests can be selected with `coverage.py`. Bugs are routed to the canonical Forgejo issue tracker. |
| `upstream/mmdebstrap/coverage.sh` | `58e90568804db9f259b9ab99ce99ed74672fe2c5` | Runs `black --check` on `tarfilter`, `coverage.py`, and `caching_proxy.py`; checks project shell files with ShellCheck and shfmt; requires the prepared mirror; with QEMU enabled, requires `shared/cache/debian-$DEFAULT_DIST.ext4`; delegates named tests to `coverage.py`. |
| `upstream/mmdebstrap/coverage.py` | `9a522484aef05deae514a98e4b6adf5feb6c886d` | Accepts test names as positional arguments, copies the checkout's `tarfilter` into `shared/`, generates `shared/test.sh`, checks that generated test with exact ShellCheck and shfmt options, then chooses `run_qemu.sh`, `run_null.sh SUDO`, or `run_null.sh`. |
| `upstream/mmdebstrap/coverage.txt` | `87f4cccf5fc646c82600672113830419e20b95dd` | Declares `Test: tarfilter-idshift` with `Needs-QEMU: true`. |
| `upstream/mmdebstrap/debian/tests/control` | `58582587412629e180ba1712abd35b8d7f7bc7de` | Declares relevant test dependencies including Black, ShellCheck, shfmt, Python 3, `libcap2-bin`, QEMU-facing suite dependencies, and the package test entry point. |
| `upstream/mmdebstrap/debian/tests/testsuite` | `9f4eda87430da38b08a23a50a51e53b22cf7414b` | The Debian autopkgtest creates one shared mirror cache, then runs `coverage.sh` with `HAVE_QEMU=no` and `HAVE_BINFMT=no`; tests marked `Needs-QEMU` are skipped in that phase. |

No separate `CONTRIBUTING` file was found in the imported mmdebstrap tree. The README points bug reports to the canonical Forgejo issue tracker. That routing fact does not authorize contact.

## Exact focused gate

After applying both retained patches to the exact current upstream checkout, the project-aligned focused command is:

```sh
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

`make_mirror.sh` may be a no-op when its Debian unstable cache is current. The first invocation still establishes the required local cache and QEMU image prerequisites.

The named command is preferable to invoking the shell test directly because it also exercises the project's test rendering, lint, formatting, runner selection, and local-source copy path.

## Automatic checks performed by that command

Before and during the named test, the project runner performs these relevant checks:

```sh
black --check ./tarfilter
```

The generated `shared/test.sh` is checked with:

```sh
shellcheck --exclude=SC2050,SC2194,SC2016 -f gcc shared/test.sh
shfmt --posix --binary-next-line --case-indent --indent 2 --simplify -d shared/test.sh
```

The complete `coverage.sh` wrapper also checks its listed project shell scripts. For this unit, the decisive changed-file checks are Black on `tarfilter` and the generated-test ShellCheck/shfmt pass for `tests/tarfilter-idshift`.

## QEMU requirement and autopkgtest coverage gap

`coverage.txt` marks `tarfilter-idshift` as `Needs-QEMU: true`.

`coverage.py` behaves as follows:

- with `HAVE_QEMU=yes`, the test runs through `./run_qemu.sh`;
- with `HAVE_QEMU=no`, a `Needs-QEMU: true` test is skipped;
- the Debian autopkgtest explicitly exports `HAVE_QEMU=no` because its environment lacks the KVM and binfmt facilities it expects.

Therefore a green Debian autopkgtest alone does not demonstrate this named test. Readiness requires one explicit QEMU-backed `tarfilter-idshift` run on the exact candidate head, or a separately reviewed project-supported execution mode that actually runs the test instead of skipping it.

## Intended exact-head sequence

```sh
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git checkout -b linux-fieldwork/unit-19-tarfilter-pax-idshift

packet=/path/to/linux-fieldwork/upstream-packets/units/19-tarfilter-pax-idshift

git apply --check "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply --check "$packet/patches/0002-tests-cover-pax-idshift.patch"
git apply "$packet/patches/0001-tarfilter-regenerate-shifted-pax-ownership.patch"
git apply "$packet/patches/0002-tests-cover-pax-idshift.patch"

git diff --check
git diff -- tarfilter tests/tarfilter-idshift
black --check ./tarfilter
./make_mirror.sh
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
CMD=./mmdebstrap ./coverage.sh tarfilter-idshift
```

Run the same named command twice after cleanup to establish an immediate rerun receipt. Record whether the second `make_mirror.sh` step is unnecessary because the cache remains current; avoid regenerating the cache without a reason.

## Current execution-environment result

The current worker environment has Python `3.13.5` and GNU patch `2.8`. It lacks `black`, `shellcheck`, and `shfmt`. DNS resolution for GitHub and the canonical Forgejo host also fails. The exact project formatting/lint and QEMU-backed gate were therefore not executed in this pass.

This is an environment/tooling limit. It does not weaken or convert the required gates into optional checks.

## Submission implications

Before `READY FOR AUTHORIZATION`, the unit must record:

1. exact current upstream base and candidate head;
2. clean application of both retained patches;
3. Black success for `tarfilter`;
4. generated-test ShellCheck and shfmt success;
5. one QEMU-backed named `tarfilter-idshift` success;
6. immediate rerun success and cleanup state;
7. complete two-file diff review;
8. current overlap recheck;
9. controlled fork/branch or another approved delivery path;
10. explicit authorization before any public action.

## Authority

Internal instruction review, patch preparation, local validation, and packet updates are authorized. No upstream issue, pull request, comment, email, review, reaction, or other external action is authorized or occurred.