# Tests

## Environment

```text
Python 3.13.5
GNU patch 2.8
git 2.47.3
Linux 6.12.13 x86_64 GNU/Linux
```

## Exact inputs

- Baseline source blob: `ad776167a8473d5d15dbe22e850f4f6db35cf278`
- Baseline source SHA-256: `442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957`
- Patch SHA-256: `2a62ae1ff84c1c613a0db89d1172e7f987164a472df0ea5da0e3b5b9037388c8`
- Candidate source SHA-256: `fdd55d9a6737bf1b5992da0254b0d6804f2b7f7598a385ed2f5b50f5196991de`
- Test SHA-256: `e9d4fc52860b718a6997c16770b98482c610a7016f0cd369c8da042ed113cc3d`

## Baseline

Command:

```sh
MMTARFILTER=/tmp/tarfilter-baseline /tmp/tarfilter-path-dotfiles
```

Result: exit `1`.

First failure:

```text
AssertionError: {'..name', '../config', '...name', '/./.config', '././config', './.config', './config', 'config', '/config', '.config', '././.config'}
```

Interpretation: `--path-exclude=/.config` retained every dotfile spelling. See `artifacts/baseline-native-test.txt`.

A detailed Python unittest variant ran five independent assertions. Baseline result: five failures. The failures covered the direct dotfile mismatch, inverse plain-name alias, include restoration, multi-dot identity, and `../config` alias.

## Patch application

Command:

```sh
patch -p1 -d /tmp/unit20-final-apply \
  -i /tmp/0001-tarfilter-preserve-dotfile-identity.patch
```

Result: exit `0`.

```text
patching file coverage.txt
patching file tarfilter
patching file tests/tarfilter-path-dotfiles
```

No fuzz or offset was reported. See `artifacts/patch-apply.txt`.

## Compilation

Command:

```sh
python3 -m py_compile /tmp/unit20-final-apply/tarfilter
```

Result: exit `0`.

## Candidate

Command:

```sh
MMTARFILTER=/tmp/unit20-final-apply/tarfilter \
  /tmp/unit20-final-apply/tests/tarfilter-path-dotfiles
```

Result: exit `0`; stdout and stderr empty.

The test covers both exclude directions, two include-after-exclude cases, repeated and alternating archive prefixes, `.config`, `..name`, `...name`, ordinary names, and `../config`. See `artifacts/candidate-native-test.txt`.

## Cleanup and rerun

The first temporary apply tree was removed. A fresh tree was created from the unmodified source and registry context, the retained patch was applied again, the candidate was compiled, and the same command ran immediately.

Result: exit `0`; stdout and stderr empty. See `artifacts/candidate-rerun.txt`.

No child processes, mounts, sockets, archives, or temporary trees were intentionally retained outside the packet files.

## Complete diff review

Reviewed files:

- `tarfilter` — one helper and one call-site replacement;
- `coverage.txt` — one test registration;
- `tests/tarfilter-path-dotfiles` — focused regression.

The diff contains no parent-retention, sparse, no-option, transform, PAX, strip, type, or link-target changes.

## Tests not run

- `CMD=./mmdebstrap ./coverage.py tarfilter-path-dotfiles` in a complete checkout at upstream main `77ec9be5417ee44c96343d2347145585da1b1f94` — complete checkout/fork unavailable.
- Full `coverage.sh` suite — disproportionate before the focused registered test runs in a full checkout.
- Debian package/autopkgtest execution — candidate has not yet been placed in a package tree.
- Cross-version Python matrix — focused execution used Python 3.13.5, matching the retained reproducer environment.

## First incomplete gate

Run the registered test through upstream `coverage.py` on the exact current main checkout, then preserve its receipt and complete diff.
