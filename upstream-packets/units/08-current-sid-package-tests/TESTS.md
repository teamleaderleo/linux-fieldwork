# Tests and receipts

## Exact baseline

- Upstream repository: `https://salsa.debian.org/debian/mmdebstrap.git`
- Revision: `debian/1.5.7-3`
- Commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Local import: `upstream/mmdebstrap`
- Import timestamp: `2026-07-30T02:32:45Z`

## Historical distinguishing matrix

| Behavior | Baseline result | Candidate/carrier result | Exact evidence |
| --- | --- | --- | --- |
| Deb822 source paragraph | `sourcesfilter` asserts on `Deb822SourceEntry`. | Raw paths rooted before `exploded_list()`; package matrix advances. | #119; PR #72 run `30546575662`; artifact digest `sha256:069449…`; console SHA-256 `0f01d4…`. |
| Stable command after `chdir` | Relative temporary proxy unavailable after directory change. | Absolute temporary proxy cleared the carrier failure; upstream series distills `/usr/bin/mmdebstrap`. | PR #72 run `30578966104`; repaired carrier head `08445ac9b02889f8b2ff6776e06d1083ace5be09`. |
| Process-group SIGINT | `/bin/kill --signal INT -- -PGID` rejected, status 1. | dash builtin short spelling delivered to both group members and returned 0. | PR #326 sid run `30635739060` / 10; artifact `8795229704`; digest `sha256:60daebe3f700d384c15414a1d6f5317532c2c73b22f863eef0dda730a978a529`. |
| Hook conflict | file-mirror hook attempted `mount --bind` after `CAP_SYS_ADMIN` drop. | Hook-free hard phase reached real `/usr/bin/mmdebstrap`. | #153; PR #72 run sequence. |
| Missing focused fixture | capability command completed, then `tar1.txt` was absent. | `create-directory` immediately preceded consumer. | PR #72 run `30633385029` / 939. |
| Stale broad fixture | focused pair passed; broad `unshare-as-root-user` compared host-hook archive with hook-free baseline and failed on three APT paths. | broad phase executed `create-directory` again. | PR #72 run `30636627420` / 974; artifact `8796132761`; digest `sha256:8e0ab3…`. |
| Phase-correct composition | previous run stopped at stale fixture. | focused producer/consumer and later broad producer passed; 154 tests completed; next failure `chrootless`. | PR #361 run `30640356619` / 999; exact generation `c2b7c43a4b6ce883f6dcdbef8d489bcf48323266`; artifact `8798679560`; digest `sha256:50d8ab7a20cb241ff9821b35329508ecdb0c58cbd3dec348c18d68d1dfe7a244`. |

## Focused repository gates already executed on predecessor source

### Hook-free scheduling

- PR #171 exact head `6469430c8fab67f9628d3346d2666e9ab7101ba5`.
- Linux Fieldwork CI `30582150648` / 633 passed selector-status, hard child status, timeout, empty-selection, syntax, application, cleanup, and rerun controls.
- PR #359 exact head `80963ab670b6d8c7595e3eb899c1601743d6176c`.
- Linux Fieldwork CI `30639443666` / 995 tested generated merge `31c9db266de5408427067f543a98327ba710c849` and reported one patch/four hunks, 369 retained tests, all passed.

### Process-group spelling

- PR #326 exact head `99faa0e8eecc95c1ef24fa53d3bdaa9309bb2c89`.
- Linux Fieldwork CI `30635739009` / 963 passed.
- Dedicated current-sid gate `30635739060` / 10 applied the selector patch with no fuzz or offset, ran twice, and selected `dash-builtin-short` both times.
- Environment receipt: dash `0.5.12-12`, procps `2:4.0.6-3`, Python `3.14.6-1`, patch `2.8-2`.

## Exact distilled-series gate

State: `PENDING`.

Run from repository root after a fresh checkout of this unit branch:

```sh
set -eu
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cp -a upstream/mmdebstrap "$work/mmdebstrap"
cd "$work/mmdebstrap"
while IFS= read -r patch_name; do
    patch --batch --forward --fuzz=0 -p1 < "$OLDPWD/upstream-packets/units/08-current-sid-package-tests/patches/$patch_name"
done < "$OLDPWD/upstream-packets/units/08-current-sid-package-tests/patches/series"
python3 -m py_compile coverage.py debian/tests/sourcesfilter
sh -n debian/tests/testsuite tests/sigint-during-customize-hook
```

Required receipt checks:

- every patch prints only the expected file names;
- zero `fuzz` and zero `offset` text;
- transformed Python compilation succeeds;
- transformed shell syntax succeeds;
- cleanup removes the temporary copy;
- the complete command passes immediately on a second fresh copy.

## Upstream-native focused execution gate

State: `PENDING`.

Minimum focused plan on the exact distilled head:

1. run the Deb822 sourcesfilter regression with current `python3-apt`;
2. run `create-directory root-without-cap-sys-admin` through the package phase with no mount-dependent hooks;
3. rerun broad `create-directory unshare-as-root-user` with host hooks;
4. run `sigint-during-customize-hook` on current sid;
5. execute the Debian package `testsuite` until the next independent result;
6. retain exact package versions, checkout identity, command, status, first failure, and artifact digest.

## Complete-diff and overlap gates

- complete diff reviewed against imported `debian/1.5.7-3`: source ownership reviewed; exact application pending;
- active overlap searched in Linux Fieldwork carriers: complete;
- live Salsa `master` overlap search: pending because the live tree could not be downloaded in this environment;
- destination contribution-path check: Salsa project identified; fork/MR remains unauthorized.

## Cleanup and rerun

Historical run 999's privileged container exited and artifact upload completed. The current pass created only Git branch files and made no local mounts, sockets, packages, containers, or persistent processes.

The exact distilled-series command has yet to run, so its cleanup/rerun result remains open.

## Tests not run

- fresh zero-fuzz/zero-offset application of all four distilled patches;
- focused upstream-native tests on the distilled exact head;
- current sid package execution without LF proxy/workflow machinery;
- live Salsa-master rebase and overlap check;
- literal upstream candidate branch CI.

Adjacent green carriers do not substitute for these gates.
