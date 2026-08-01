# Tests and receipts

## Exact identities

| Item | Identity |
| --- | --- |
| Upstream base | `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Imported source blob | `bb7bce0fd6e37d61a063b1ccb0700a6c8c0cf7b3` |
| Packet patch | `patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch` |
| Packet patch SHA-256 | `0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd` |
| Packet regression | `tests/test_packet_patch.py` |
| Repository regression | `../../../tests/test_unit04_qemu_packet_patch.py` |
| Reduced lifecycle model | `scripts/verify_lifecycle_model.py` |
| Internal CI carrier | draft PR #400; run `30675270148` |

## Initial packet run

Command:

```text
cd /mnt/data/unit04-work
python3 -m unittest -v tests/test_packet_patch.py
```

Result on 2026-07-31 PDT:

```text
test_cleanup_precedence ... ok
test_failure_preserves_existing_and_absent ... ok
test_hup_int_term_and_rerun ... ok
test_patch_applies_without_offset_or_fuzz_to_exact_imported_source ... skipped (source tree unavailable in container)
test_success_mode_and_post_publication_term ... ok
test_trailing_slash_rejected_before_mktemp ... ok
test_upstream_paths_coordinates_and_single_publication ... ok
Ran 7 tests in 1.087s
OK (skipped=1)
```

Complete transcript: `test-output.txt`.

## Repaired reduced model run

The first run of `scripts/verify_lifecycle_model.py` passed two cases and failed the trailing-slash case with `AssertionError: 42 != 1`. `pathlib.Path(f"{destination}/")` had removed the trailing slash before process invocation. This was a test-tooling defect; the patch was unchanged.

Repair: allow `pathlib.Path | str` in the runner and pass the original trailing-slash spelling as a string.

Rerun:

```text
test_baseline_term_resumes_but_candidate_terminates ... ok
test_failure_success_and_late_signal_publication ... ok
test_trailing_slash_rejected_before_private_state ... ok
Ran 3 tests in 1.240s
OK
```

## Current repository gate

Commit `6d5afb1aea17e44b665c1e74e95aba86dd50d3cc` added:

```text
tests/test_unit04_qemu_packet_patch.py
```

The test requires:

1. upstream-root patch paths;
2. complete-file hunk starts at 318, 406, 465, 474, and 483;
3. `patch --batch --forward --fuzz=0 -p1` success against the exact imported source;
4. an application transcript containing neither `offset` nor `fuzz`;
5. complete candidate `sh -n` success;
6. `mke2fs`, `truncate`, `sfdisk`, and `dd` routed to `IMAGE_TMP`;
7. exactly one publication rename;
8. the repaired three-test lifecycle model passing.

Draft internal PR #400 triggered Linux Fieldwork CI run `30675270148`. At this document update the run remains queued; record its final job and result in `HANDOFF.md` or the next `TESTS.md` update.

## Dynamic cases completed locally and historically

- Existing final plus ordinary failure: status 42, bytes and mode preserved, private state removed.
- Absent final plus ordinary failure: destination remains absent, private state removed.
- Baseline parent-only TERM: cleanup returns, later marker runs, status 0.
- Candidate wrapper-only HUP/INT/TERM: statuses 129/130/143, later marker absent, prior output preserved.
- Immediate rerun after each tested signal: complete bytes published.
- Successful publication: complete bytes and mode 0644 under umask 022.
- TERM after publication: status 143, published image retained.
- Cleanup precedence: cleanup failure 74 after clean success; command failure 42 and signal results remain primary.
- Trailing slash: status 1 before private state.
- Packet layout: upstream-root paths, one publication operation, complete-file hunk coordinates.

## Canonical carrier gates retained

PR #195 exact head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` passed Linux Fieldwork CI run `30578489526`, including job `90992563661`. Eight focused tests covered lifecycle and path behavior. The complete four-file diff was reviewed. These runs validate the composed behavior against the same imported source blob.

## Red and neutral runs classified

1. Initial packet harness red: method `run` shadowed `unittest.TestCase.run`. Test-tooling defect; renamed to `run_harness`. Product patch unchanged.
2. Second packet harness red: function extraction found `cleanup()` inside `exit_cleanup()` and could not reconstruct unchanged declaration text. Test-tooling defect; extraction now anchors complete function markers. Product patch unchanged.
3. Reduced-model trailing-slash red: `pathlib.Path` removed the spelling being tested. Test-tooling defect; the runner now preserves the raw string. Product patch unchanged.
4. Exact-source local packet test skipped: the first container lacked the repository source and direct clone failed DNS resolution. The repository regression now owns this gate.
5. `shellcheck` and `shfmt` were absent locally. Upstream `coverage.sh` identifies both as native static gates for this file.
6. Branch-only workflow lookup returned no run because Linux Fieldwork CI uses pull-request events. Draft internal PR #400 now carries the branch through CI.

## Upstream-native entry points

Upstream `coverage.sh` checks the builder with:

```text
shellcheck --exclude=SC2016 mmdebstrap-autopkgtest-build-qemu
shfmt --binary-next-line --case-indent --indent 2 --simplify -d \
  mmdebstrap-autopkgtest-build-qemu
```

No focused dynamic QEMU-builder test was found in `coverage.txt`. A real builder gate therefore requires direct invocation on a Debian host with the builder dependencies and a usable mirror.

## Exact next commands

From Linux Fieldwork:

```text
python -m unittest -v tests/test_unit04_qemu_packet_patch.py
python -m unittest -v \
  upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py \
  tests/test_qemu_builder_composed_lifecycle.py \
  tests/test_qemu_builder_composed_lifecycle_paths.py
```

From an upstream checkout at `77ec9be5417ee44c96343d2347145585da1b1f94`:

```text
patch --batch --forward --fuzz=0 -p1 \
  -i /path/to/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch
sh -n mmdebstrap-autopkgtest-build-qemu
shellcheck --exclude=SC2016 mmdebstrap-autopkgtest-build-qemu
shfmt --binary-next-line --case-indent --indent 2 --simplify -d \
  mmdebstrap-autopkgtest-build-qemu
```

Real builder gate:

```text
./mmdebstrap-autopkgtest-build-qemu \
  --boot=efi --arch="$(dpkg --print-architecture)" \
  unstable /tmp/unit04-autopkgtest.img
```

Record output digest and mode, absence of private sibling residue, immediate rerun behavior, and final image cleanup.

## Cleanup

All local dynamic work used `TemporaryDirectory` and owned subprocesses which were waited. No process, socket, mount, container, image, or package mutation remains. The committed packet, tests, and draft internal PR are intentional retained state.
