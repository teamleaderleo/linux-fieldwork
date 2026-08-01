# Tests and evidence

## Test identity

| Item | Value |
| --- | --- |
| Canonical upstream base | `josch/mmdebstrap` `main` `77ec9be5417ee44c96343d2347145585da1b1f94` |
| Controlled fork/base | `teamleaderleo/mmdebstrap`, `linux-fieldwork/upstream-main-snapshot` at the same commit |
| Controlled candidate branch | `linux-fieldwork/unit-15-tarfilter-transform-metadata` |
| Controlled candidate head | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Candidate source commit | `f7833615824ad99023c21a495840d10f64c6401a` |
| Native-test commit | `f7337a7d2f33d280c8e5b1576dd729f4d076c13a` |
| Coverage-registration commit | `505bf81079a3b76c7d56bffa8097c1b5a494898e` |
| Linux Fieldwork branch | `upstream/unit-15-tarfilter-transform-metadata` |
| Runtime | Python 3.13.5; GNU tar 1.35; GNU patch 2.8 |
| Kernel/architecture | Linux 6.12.13, x86_64 |
| Privilege boundary | unprivileged archive creation, filtering, inspection, and extraction in disposable directories |

## Exact file identities

```text
baseline tarfilter Git blob:
  ad776167a8473d5d15dbe22e850f4f6db35cf278
baseline tarfilter SHA-256:
  442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957
candidate tarfilter Git blob:
  adb330efcc941bf5e646f195c245a3184e42f8e2
candidate tarfilter SHA-256:
  adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e
native test Git blob:
  bc9fb4e0593df5a37dee986308ebb62abc4b6839
native test SHA-256:
  adab3852d9c8e719d64a24e1aed386d2eeccb45a43922f854d7458aa486f8caa
coverage.txt Git blob after registration:
  fdac8b9f86b04e48af6476c32b649b1ed4bda95a
regenerated source patch SHA-256:
  4d8cb2f180cb7798a15195c2dcfac164b409f68a18c69d507cfc624d4725703c
controlled-fork native receipt SHA-256:
  74d0ceff423a8bbc57bd5e8ae4dff3aa6ba1cfc105ebdbfd47d717f9e20f33a1
packet matrix JSON SHA-256:
  325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106
```

## Controlled fork diff

Comparison from `linux-fieldwork/upstream-main-snapshot` to `linux-fieldwork/unit-15-tarfilter-transform-metadata`:

```text
base and merge base: 77ec9be5417ee44c96343d2347145585da1b1f94
head: 505bf81079a3b76c7d56bffa8097c1b5a494898e
status: ahead
ahead_by: 3
behind_by: 0
files:
  coverage.txt                         +2   -0
  tarfilter                          +179  -23
  tests/tarfilter-transform-metadata +250  -0
```

The three commits separate source materialization, native-test addition, and test registration. They do not represent a decided upstream series shape.

## Native test location and ownership

- Test file: `tests/tarfilter-transform-metadata`
- Registration: `coverage.txt` paragraph `Test: tarfilter-transform-metadata`
- Upstream runner behavior: `coverage.py` verifies one-to-one filename/paragraph registration, copies the selected test into `shared/test.sh`, runs shellcheck and shfmt, and executes through `run_null.sh`, `run_qemu.sh`, or sudo according to the test configuration.
- This test has no root, QEMU, or APT-config marker, so the runner would select the null path in a complete checkout.

## Exact direct native rerun

The rerun used two disposable source roots. Both contained the same native test. The baseline root was produced by reverse-applying the clean packet patch with zero fuzz; the candidate root contained the exact fork source bytes.

### Baseline preparation and command

```sh
patch --fuzz=0 -R -p1 -d /mnt/data/unit15-native-rerun/baseline \
  -i /mnt/data/unit15-local/patch.diff

cd /mnt/data/unit15-native-rerun/baseline/upstream/mmdebstrap/tests
./tarfilter-transform-metadata
```

Observed:

```text
reverse patch status: 0
baseline source SHA-256: 442b056aeb414aef0e33d59b6235623ca4d6072c62272508281d126cb3f3d957
test status: 1
stdout: empty
first stderr line: Traceback (most recent call last):
last stderr line: AssertionError: s/a/b/
```

The assertion is the intended first-versus-global losing control. The old implementation changes `a/a` to `b/b`; the expected GNU behavior is `b/a`.

### Candidate syntax and command

```sh
python3 -m py_compile \
  /mnt/data/unit15-native-rerun/candidate/upstream/mmdebstrap/tarfilter

sh -n \
  /mnt/data/unit15-native-rerun/candidate/upstream/mmdebstrap/tests/tarfilter-transform-metadata

cd /mnt/data/unit15-native-rerun/candidate/upstream/mmdebstrap/tests
./tarfilter-transform-metadata
./tarfilter-transform-metadata
```

Observed:

```text
Python compile status: 0
POSIX shell syntax status: 0
candidate run 1 status: 0
candidate run 1 stdout: tarfilter transform metadata: PASS
candidate run 1 stderr: empty
candidate run 2 status: 0
candidate run 2 stdout: tarfilter transform metadata: PASS
candidate run 2 stderr: empty
matching leftover temporary directories: 0
```

Receipt: `artifacts/FORK_NATIVE_TEST.txt`.

### Formatting tool availability

```text
shellcheck: NOT_INSTALLED
shfmt: NOT_INSTALLED
```

Those are unexecuted gates, not failures.

## Native test matrix

| Case | Baseline or predecessor | Candidate | Reference/control |
| --- | --- | --- | --- |
| Ordinary replacement | `a/a -> b/b`; native test stops | `a/a -> b/a` | GNU tar |
| Global replacement | `g` rejected | `a/a -> b/b` | GNU tar |
| Whole-match `&` | unsupported semantics | `[a]/a` | GNU tar |
| Escaped delimiter | narrow parser boundary | `x#y/a` | GNU tar |
| Default target scopes | link targets remain prefixed | default `rsh` | GNU tar |
| Uppercase `S` | no scope model | symlink target preserved | GNU tar |
| Hard-link extraction | transformed target unavailable | extraction succeeds and inode is shared | filesystem assertion |
| Long PAX strip | stale prefixed `path`/`linkpath` | regenerated leaf values | archive inspection and extraction |
| Numeric selectors | PR #68 predecessor rejects | `2`, `2g`, `g2`, `0`, `0g`, `22`, `2g3`, `i2g` pass | GNU tar |
| Non-ASCII numerals | unsupported | rejected | negative control |
| Cleanup/rerun | n/a | two passes, no leftovers | `/tmp` scan |

## Packet-owned matrix

The packet wrapper remains the broad retained differential:

```sh
upstream-packets/units/15-tarfilter-transform-metadata/scripts/materialize_and_run.sh \
  > /tmp/unit15-matrix.json
```

Observed across three direct executions plus one wrapper execution:

```text
status: PASS
Python: 3.13.5
GNU tar: 1.35
candidate SHA-256: adb1a8353bcd676a8acdba4318b198539820b890e2a96016b9909d382942e42e
JSON SHA-256: 325db677bba5b435c45de2f09f89b2f52fd88e62137660094457623adb1e8106
```

The packet matrix additionally retains the PR #68 predecessor rejection, independent numeric counting for link targets, and exact source blob check.

## Patch application

Selected source application:

```sh
patch --fuzz=0 -p1 -d /path/to/mmdebstrap \
  -i upstream-packets/units/15-tarfilter-transform-metadata/patches/0001-tarfilter-transform-metadata.patch
```

Observed: status `0`, no fuzz, no offsets, and candidate bytes exactly equal to the controlled-fork source. Historical PR #68 plus PR #102 Git patches remain provenance; their offset behavior and GNU patch 2.8 parser-hunk rejection are recorded in `artifacts/APPLICATION.txt`.

## Upstream-native gate table

| Gate | Exact command or entry point | Result | Exact candidate |
| --- | --- | --- | --- |
| Native test direct baseline | `tests/tarfilter-transform-metadata` against exact baseline | EXPECTED FAIL, status 1 at first replacement | baseline blob `ad776167...` |
| Native test direct candidate | same test against fork source | PASS twice, status 0 | fork head `505bf810...` source bytes |
| Python syntax | `python3 -m py_compile tarfilter` | PASS | source SHA-256 `adb1...` |
| Shell syntax | `sh -n tests/tarfilter-transform-metadata` | PASS | test SHA-256 `adab...` |
| `coverage.txt` registration | exact filename paragraph added | PRESENT; structural diff reviewed | coverage blob `fdac...` |
| `coverage.py` selected test | `CMD=./mmdebstrap ./coverage.py tarfilter-transform-metadata` in full checkout | NOT RUN | fork head `505bf810...` |
| shellcheck | runner arguments from `coverage.py` | NOT RUN; tool absent | fork head `505bf810...` |
| shfmt | runner arguments from `coverage.py` | NOT RUN; tool absent | fork head `505bf810...` |
| relevant package/build tests | project-specific full checkout gates | NOT RUN | fork head `505bf810...` |
| hosted CI | controlled fork workflow, if configured | NOT RUN | fork head `505bf810...` |

## Historical exact-head receipts

- PR #56: workflow `30535166174` success on `640f414cb18cf47b3e803856392c720414bea333`.
- PR #68: workflow `30536181358` success on `1f8f16bf0841a720bdc1da727000c26a3ab13a09`.
- PR #102: workflow `30543327305` success on `46f49d04639d6baf43243e5096175866c7e6a58e`; corrected code run `30543032983`; initial differential `30542362599`.

These receipts support provenance. The direct controlled-fork rerun is the current-head evidence.

## Environment and interruption classification

An attempted local `git clone` of the controlled fork failed because the execution container could not resolve `github.com`. The connected GitHub repository API remained available and was used to create and inspect the branch. This is an environment/network result, not a product or patch failure.

## Cleanup

The native fixture uses Python `TemporaryDirectory` instances. After the baseline run and two candidate runs, a `/tmp` scan found zero directories matching:

```text
tarfilter-transform-*
tarfilter-targets-*
tarfilter-pax-*
tarfilter-occurrence-*
```

No process, socket, mount, package state, cache entry, or external repository object was left running or modified. Intentional state is the controlled fork branch and Linux Fieldwork packet.

## Tests not run

- selected test through the complete `coverage.py`/`run_null.sh` path;
- shellcheck and shfmt;
- complete `coverage.sh` suite;
- Debian package build and autopkgtest;
- other GNU tar and Python versions;
- other architectures and distributions;
- unit 01 regex-dialect composition;
- persistent `flags=`, expression lists, case conversion, locale/collation, and broad malformed-expression parity.

## Final evidence statement

The controlled fork at `505bf81079a3b76c7d56bffa8097c1b5a494898e` is exactly based on canonical upstream `77ec9be5417ee44c96343d2347145585da1b1f94` and contains only the source candidate, one native regression, and its registration. The exact baseline loses the native test at the first replacement discriminator. The exact candidate passes that test twice, passes Python and shell syntax, matches the retained GNU tar differential matrix, extracts hard links correctly, regenerates tested PAX metadata, and leaves no matching temporary state. The conclusion stops before execution through the complete upstream runner, formatting tools, package gates, hosted CI, and broader environment coverage.
