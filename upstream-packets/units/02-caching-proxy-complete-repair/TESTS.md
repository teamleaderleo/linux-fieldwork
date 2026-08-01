# Tests and receipts

## Source identities

- imported baseline: `upstream/mmdebstrap/caching_proxy.py`, Git blob `e57a8516a0c76167894b05fc56be0e3165535488`;
- complete internal candidate: PR #198 final head `5e69cd25e62d0e86364459d97c9df8568ff84187`;
- final internal merge: `8d9f7fa92f0cb2f553ca3578b78d7e04f4e4167f`;
- current upstream head observed: `77ec9be5417ee44c96343d2347145585da1b1f94`;
- packet branch: `upstream/unit-02-caching-proxy-complete-repair`.

## Internal complete-matrix receipts

Command:

```text
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

Recorded local results in the merged investigation:

```text
Ran 7 tests in 16.425s
OK

snapshot-packaging rerun:
Ran 7 tests in 15.297s
OK
```

Hosted exact-head result:

```text
head: 5e69cd25e62d0e86364459d97c9df8568ff84187
workflow: Linux Fieldwork CI
run: 30580697438 / 612
result: success
```

Predecessor composed-source result:

```text
head: 00caba3d753536dd9a3a68fc6f110c75e338ec08
workflow: Linux Fieldwork CI
run: 30578916643 / 572
result: success
```

Focused receipts retained by the composition:

| Carrier | Exact head or merge | Run | Result |
| --- | --- | ---: | --- |
| PR #118 request containment | repaired focused carrier retained by #198 | 541 | success |
| PR #139 request headers | merge `caf3262d2aa85057a2793bf758c7fc488bd0ccf2` | 344 | success |
| PR #147 post-commit errors | repaired focused carrier retained by #198 | 542 | success |
| PR #162 canonical core | `055999d4c2d157abb9cb3d6dbf77a8cdacc91b1d` | 551 / CI `30578489609` | success |
| PR #169 origin status | `3ae3a6501653f273af25adae0279d072795e5a2f` | 431 / CI `30557655364` | success |

## Complete behavior matrix

### Request rejection and zero side effects

- unsupported methods;
- missing, duplicate, malformed, or authority-conflicting `Host`;
- duplicate `Content-Length`;
- non-decimal, nonzero, or empty length;
- request `Transfer-Encoding`;
- userinfo, query, fragment, malformed ports, origin-form targets;
- percent escapes, NUL, literal backslash, empty/dot/dot-dot components, doubled and trailing separators;
- lexical and existing-symlink cache escapes;
- ordinary and optimized Python.

Required result: rejection occurs before cache directory creation, cache lookup/mutation, or origin contact.

### Origin request boundary

- mixed-case `Proxy-Authorization`;
- `Proxy-Connection`;
- standard request hop-by-hop fields;
- fields nominated by `Connection` tokens;
- duplicate safe end-to-end fields;
- duplicate Host and `Connection: Host` rejection.

Required result: blocked fields never reach the loopback origin; repeated safe fields remain separate; one explicit origin `Connection: close` is present.

### Origin response and framing

- origin non-200 under normal and `python -O`;
- 200 with custom reason phrase;
- valid fixed-length response;
- valid exact chunked response with conflicting origin `Content-Length`;
- EOF-delimited response;
- malformed, negative, and short declared lengths;
- unsupported and compound transfer codings;
- response hop-by-hop fields and `Connection`-nominated fields.

Required result: invalid status or framing fails before downstream commitment and cache publication. Supported responses preserve bytes and end-to-end headers.

### Publication, retry, and late failure

- hidden exclusive temporary creation;
- final pathname absent during a synchronized fill;
- premature EOF cleanup and retry;
- cache writer open/write failure;
- downstream disconnect;
- post-header origin read failure;
- post-prefix origin read failure;
- concurrent misses;
- final file mode;
- no temporary residue.

Required result: final name appears only after complete receipt; failed fills leave no final or temporary object; late failures produce one committed status and close; retry reaches the origin and recovers.

### Lifecycle cleanup

- origin connections closed in `finally`;
- clients explicitly closed;
- servers shut down and close;
- server threads joined;
- subprocesses terminated and waited;
- temporary roots removed;
- rerun succeeds from clean state.

## Current packet work

### Added

`./upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh`

The exporter:

1. resolves the checkout root;
2. runs the merged semantic composer;
3. compiles the generated candidate;
4. writes `patches/0001-caching-proxy-complete-repair.patch`;
5. records the checkout head, imported Git blob, candidate SHA-256, patch SHA-256, line counts, and compile result in `artifacts/export-receipt.txt`.

### Execution state

`UNEXECUTED IN THIS SESSION`.

Reason: repository source was available through the GitHub connector while the execution container lacked network access and had no mounted checkout. The script has therefore been retained for the first full-checkout action. No pass is claimed.

## Exact commands for the next checkout

Identity gate:

```sh
git -C /path/to/mmdebstrap rev-parse HEAD
git -C /path/to/mmdebstrap hash-object caching_proxy.py
```

Expected upstream commit:

```text
77ec9be5417ee44c96343d2347145585da1b1f94
```

Expected source blob for a clean direct export:

```text
e57a8516a0c76167894b05fc56be0e3165535488
```

Packet exporter:

```sh
./upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh
cat upstream-packets/units/02-caching-proxy-complete-repair/artifacts/export-receipt.txt
```

Internal complete matrix against the generated source mechanism:

```sh
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

Clean rerun:

```sh
rm -rf upstream-packets/units/02-caching-proxy-complete-repair/artifacts/export
./upstream-packets/units/02-caching-proxy-complete-repair/scripts/export_candidate.sh
python3 -m unittest -v tests/test_caching_proxy_complete_stack.py
```

Patch application gate in an exact upstream checkout:

```sh
git -C /path/to/mmdebstrap checkout --detach 77ec9be5417ee44c96343d2347145585da1b1f94
git -C /path/to/mmdebstrap apply --check /path/to/0001-caching-proxy-complete-repair.patch
git -C /path/to/mmdebstrap apply /path/to/0001-caching-proxy-complete-repair.patch
python3 -m py_compile /path/to/mmdebstrap/caching_proxy.py
```

## Upstream-native gates still required

- select a test location consistent with current mmdebstrap conventions;
- run focused loopback tests from the upstream checkout;
- run them under ordinary and optimized Python;
- run any repository lint/format gate that covers Python files;
- run the relevant mmdebstrap test selector, if the focused test is wired into `coverage.py` or `coverage.sh`;
- inspect generated patch with `git diff --check`;
- perform cleanup and exact-head rerun;
- record the candidate branch and head;
- refresh overlap search immediately before authorization.

## Cleanup state

No local checkout, candidate tree, process, socket, server, or temporary cache was created in this session. The only durable changes are commits on the internal packet branch and the internal issue claim.
