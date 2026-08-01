# Tests and receipts

## Local packet run

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

## Artifact hashes

```text
0ef272d4613e1744957630c5de7da081e248601f934aa98efb43ea22b143c4dd  patches/0001-qemu-builder-atomic-publication-and-signal-lifecycle.patch
e94d0c4b39af0d2479044d59f225d27267766828ba8e402481f866d330156f80  tests/test_packet_patch.py
f115c359b216cb723835fb1b4fe8e62a4efd27ed4fe98d57b375ae8646e9a102  test-output.txt
```

Machine-readable copy: `SHA256SUMS`.

## Dynamic cases completed locally

- Existing final plus ordinary failure: status 42, bytes and mode preserved, private state removed.
- Absent final plus ordinary failure: destination remains absent, private state removed.
- Wrapper-only HUP/INT/TERM: statuses 129/130/143, later marker absent, prior output preserved.
- Immediate rerun after each tested signal: complete bytes published.
- Successful publication: complete bytes and mode 0644 under umask 022.
- TERM after publication: status 143, published image retained.
- Cleanup precedence: cleanup failure 74 after clean success; command failure 42 remains primary.
- Trailing slash: status 1 before `mktemp`.
- Packet layout: upstream-root paths, one publication operation, full-file hunk coordinates.

## Canonical carrier gates retained

PR #195 exact head `b7fbc7e6dcf40e95d17b7cb67fc96c710571f154` passed Linux Fieldwork CI run `30578489526`, including job `90992563661`. Eight focused tests covered lifecycle and path behavior. These runs validate the composed behavior against the imported source; this packet still needs its regenerated patch applied at zero offset.

## Red and neutral runs classified

1. Initial packet harness red: method `run` shadowed `unittest.TestCase.run`. Test-tooling defect; renamed to `run_harness`. Product patch unchanged.
2. Second packet harness red: function extraction found `cleanup()` inside `exit_cleanup()` and could not reconstruct unchanged declaration text. Test-tooling defect; extraction anchored complete function markers and reconstructs the changed cleanup body. Product patch unchanged.
3. Exact-source local test skipped: the container lacked a Linux Fieldwork or upstream checkout and direct clone failed DNS resolution. Environment limitation; the test remains mandatory in repository execution.
4. `shellcheck` and `shfmt` were absent locally. Environment limitation; upstream `coverage.sh` identifies both as native static gates for this file.

## Required next gate

From the Linux Fieldwork repository root:

```text
python3 upstream-packets/units/04-qemu-image-builder-lifecycle/tests/test_packet_patch.py
```

That run must report seven passing tests with zero skips. Then apply the patch to exact upstream `main` and run:

```text
sh -n mmdebstrap-autopkgtest-build-qemu
shellcheck --exclude=SC2016 mmdebstrap-autopkgtest-build-qemu
shfmt --binary-next-line --case-indent --indent 2 --simplify -d mmdebstrap-autopkgtest-build-qemu
```

## Cleanup

The local harness created only temporary directories and child shell processes owned by `TemporaryDirectory`/`subprocess`. No process, socket, mount, container, image, or package mutation remains. The packet files under `/mnt/data/unit04-work` are intentionally retained until committed.
