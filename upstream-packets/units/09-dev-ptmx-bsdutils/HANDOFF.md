# Handoff

## Unit state

`ACTIVE`

Unit 09 has a durable packet, a retained upstream-rooted one-line patch, exact historical ownership, and a complete carrier map. External contact remains unauthorized.

## Exact stopping point

- Linux Fieldwork branch: `upstream/unit-09-dev-ptmx-bsdutils`
- Base: `main` at `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`
- Exact branch head immediately before adding this handoff: `0ec31930b35b69125c2f4e440d004595075bc0cf`
- This `HANDOFF.md` creation is the sole content change after that pre-handoff head; resolve the branch ref for the resulting handoff commit.
- Packet: `upstream-packets/units/09-dev-ptmx-bsdutils/`
- Upstream repository: `josch/mmdebstrap` on Muffin Forgejo
- Upstream branch: `main`
- Upstream head advertised during this pass: `77ec9be5417ee44c96343d2347145585da1b1f94`
- Controlled fork: `NEEDS FORK`
- External-contact state: unauthorized; internal work only

## Completed in this pass

1. Read issue `#397`, `upstream-packets/README.md`, `upstream-packets/INDEX.md`, and the complete unit carrier chain: issue `#53`, PR `#82`, issue `#84`, PR `#86`, superseding PR `#89`, transition dossier PR `#60`, and disposable current-sid carrier PR `#72`.
2. Claimed unit 09 on issue `#397`.
3. Created branch `upstream/unit-09-dev-ptmx-bsdutils` from exact main `6cc74d846c50b9bbb88247e8a128b67e8c174c1e`.
4. Verified the imported baseline blob `ca1cde040f945fe871f904ef6a56e040b6a5c9ea` still contains `--include=gcc,libc6-dev,python3,passwd` and exactly two inner `script -c` customize hooks.
5. Recorded the historical Debian CI run `72574145`, capture identities, provider transition, and precise ownership boundary.
6. Preserved the accepted internal validation from PR `#89` exact head `9db9f4d9ae423a5c0dbd2255c05decf14fbe9d66` and CI run `30539827917`.
7. Added `patches/0001-tests-include-bsdutils-for-dev-ptmx.patch`, changing only the upstream `tests/dev-ptmx` include line.
8. Wrote source map, mechanism analysis, test matrix, decisions, issue disposition, and pull-request draft.
9. Attempted canonical network checkout. The command failed before data transfer because `gitlab.mister-muffin.de` could not be resolved in this execution environment.

## Latest distinguishing result

The exact historical failure and current imported source agree on one owner:

```text
root include: gcc,libc6-dev,python3,passwd
inner command: chroot "$1" script -c "echo foobar"
failure: chroot: failed to run command ‘script’: No such file or directory
provider: bsdutils -> /usr/bin/script
candidate: add bsdutils to the existing include list
```

The existing static regression proved a one-line delta and unchanged hook order on PR `#89`. The official repository page advertised upstream `main` at `77ec9be5417ee44c96343d2347145585da1b1f94`.

## First incomplete step

Obtain exact bytes for upstream head `77ec9be5417ee44c96343d2347145585da1b1f94` or a fresher verified `main`, then apply the packet patch with zero fuzz and zero offset.

Suggested commands:

```sh
git clone https://gitlab.mister-muffin.de/josch/mmdebstrap.git
cd mmdebstrap
git checkout 77ec9be5417ee44c96343d2347145585da1b1f94
git apply --check /path/to/0001-tests-include-bsdutils-for-dev-ptmx.patch
git apply /path/to/0001-tests-include-bsdutils-for-dev-ptmx.patch
git diff --check
git diff -- tests/dev-ptmx
```

Expected diff: one include line, adding `bsdutils` before `gcc`.

## Next safe technical action

After exact application succeeds:

1. run focused static assertions against the exact upstream checkout;
2. use the current successor of PR `#72` to execute `dev-ptmx --mode=root --variant=apt` on current sid with the patch applied only to the disposable source copy;
3. record mirror identity, package universe, candidate commit, workflow/run/artifact IDs, digest, exit status, and first result;
4. verify cleanup of root, mounts, listeners, containers, and temporary source;
5. rerun the exact focused case immediately;
6. update `TESTS.md`, `README.md`, `DECISIONS.md`, and this handoff;
7. move to `READY FOR AUTHORIZATION` only after exact-current application and the focused run/rerun pass, or retire the submission if equivalent upstream work already landed.

## Test and cleanup state

- Historical transcript: recovered and durable summary retained.
- Static candidate regression: passed previously on exact PR `#89` head.
- Exact current-upstream patch application: unexecuted because canonical host DNS failed.
- Current-sid named case: unexecuted in this unit pass.
- Cleanup/rerun: pending named case.
- This pass created no root filesystem, mount, listener, package state, container, or persistent temporary checkout.

## Authorization boundary

No upstream issue, pull request, comment, email, review, or other external contact was created. A controlled fork is still required. Obtain explicit authorization before any external mutation or contact.
