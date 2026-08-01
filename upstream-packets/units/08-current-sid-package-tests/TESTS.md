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
| Deb822 source paragraph | `sourcesfilter` asserts on `Deb822SourceEntry`. | Raw paths rooted before `exploded_list()`; package matrix advances. | #119; PR #72 run `30546575662`; artifact digest `sha256:069449b16e3448e89d7d225f811fc4707287df3ef0a99f35f491b1efc4cb52b0`; console SHA-256 `0f01d4beb61965a0c1adbb9fd5f1dc7298a1310edbf4465eb8499fc5f34e7075`. |
| Stable command after `chdir` | Relative temporary proxy unavailable after directory change. | Absolute temporary proxy cleared the carrier failure; upstream series distills `/usr/bin/mmdebstrap`. | PR #72 run `30578966104`; repaired carrier head `08445ac9b02889f8b2ff6776e06d1083ace5be09`. |
| Process-group SIGINT | `/bin/kill --signal INT -- -PGID` rejected, status 1. | dash builtin short spelling delivered to both group members and returned 0. | PR #326 sid run `30635739060` / 10; artifact `8795229704`; digest `sha256:60daebe3f700d384c15414a1d6f5317532c2c73b22f863eef0dda730a978a529`. |
| Hook conflict | file-mirror hook attempted `mount --bind` after `CAP_SYS_ADMIN` drop. | Hook-free hard phase reached real `/usr/bin/mmdebstrap`. | #153; PR #72 run sequence. |
| Missing focused fixture | capability command completed, then `tar1.txt` was absent. | `create-directory` immediately preceded consumer. | PR #72 run `30633385029` / 939. |
| Stale broad fixture | focused pair passed; broad `unshare-as-root-user` compared host-hook archive with hook-free baseline and failed on three APT paths. | broad phase executed `create-directory` again. | PR #72 run `30636627420` / 974; artifact `8796132761`; digest `sha256:8e0ab36d6938c5eb676cd8f1550dec978743c3e12d4da4c6b862602c5f407227`. |
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

State: `AUTOMATED GATE COMMITTED; EXECUTION PENDING`.

Executable gate:

- file: `tests/test_upstream_packet_unit_08_current_sid_package_tests.py`;
- introducing commit: `7782872ae2f731a27ed672df3a37b1d3b1581aa4`;
- series order is asserted exactly;
- each patch runs with `patch --batch --forward --fuzz=0 -p1`;
- receipts must name every expected patched path and contain neither `fuzz` nor `offset`;
- transformed `coverage.py` and `debian/tests/sourcesfilter` compile;
- transformed `debian/tests/testsuite` and `tests/sigint-during-customize-hook` pass `/bin/sh -n`;
- two fresh applications must produce identical candidate SHA-256 digests and identical receipts;
- imported source digests must remain unchanged.

Local syntax-only review of the gate source completed on 2026-08-01:

```text
py_compile=PASS
ast_parse=PASS
sha256=a16b060b02a7c9e1b43db600f0f5789e6e5fc3add7cf93dc95ca32ad314b3dd6
```

This receipt proves the test module parses. It does not prove the patch series applies because the session runtime lacked a materialized repository checkout.

The branch push at `7782872ae2f731a27ed672df3a37b1d3b1581aa4` produced no workflow run because Linux Fieldwork CI is `pull_request`/`workflow_dispatch` only. A draft internal PR creation attempt was blocked by the connector safety classifier. The action was not retried speculatively.

Manual equivalent from a full checkout:

```sh
python3 -m unittest -v \
  tests.test_upstream_packet_unit_08_current_sid_package_tests
```

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

Historical run 999's privileged container exited and artifact upload completed. The current pass created Git branch files and one transient local syntax-check file under `/tmp`; `/tmp/test_unit08.py` and its `__pycache__` were removed after compilation and AST parsing.

The exact distilled-series test still awaits a full repository checkout or CI execution, so its temporary-copy cleanup and immediate second-run result remain open.

## Tests not run

- execution of `tests/test_upstream_packet_unit_08_current_sid_package_tests.py` against the repository tree;
- focused upstream-native tests on the distilled exact head;
- current sid package execution without LF proxy/workflow machinery;
- live Salsa-master rebase and overlap check;
- literal upstream candidate branch CI.

Adjacent green carriers do not substitute for these gates.
