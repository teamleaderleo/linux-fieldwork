# Current-sid dev-ptmx double-pass receipt

## Scope

Two disposable Debian sid executions selected only `dev-ptmx` after the package-test mirror phase. Both used the same one-line source candidate:

```diff
-	--include=gcc,libc6-dev,python3,passwd \
+	--include=bsdutils,gcc,libc6-dev,python3,passwd \
```

Both executed the root and unshare variants through the installed Debian `mmdebstrap 1.5.7-3` package.

## Package universe

```text
apt             3.3.2            amd64
autopkgtest     6.0              all
bsdutils        1:2.42.2-2       amd64
dash            0.5.12-12        amd64
mmdebstrap      1.5.7-3          all
procps          2:4.0.6-3        amd64
util-linux      2.42.2-2         amd64
kernel          6.17.0-1020-azure
```

The generated roots used:

```text
--include=bsdutils,gcc,libc6-dev,python3,passwd
```

## Run 30690241513

```text
execution head: 501c19c7147b2452350069fda5375c4cdbc7ab7c
artifact ID: 8815599405
artifact name: mmdebstrap-reproduction-gha-30690241513-1
artifact digest: sha256:bd97c229b886501d57d4618381d1a07e446f48f6c46e409e1915f7d8675e0b82
console digest: sha256:a492438a91a79f85d85fe80bdd8a88cbec685c1c6f55b9ceb7b7bf36369fcd5c
started: 2026-08-01T07:42:04Z
finished: 2026-08-01T07:59:21Z
autopkgtest wrapper status: 2
testsuite result: PASS
```

Named results:

```text
(253/284) dev-ptmx --mode=root:    SUCCESS, 0:00:18
(254/284) dev-ptmx --mode=unshare: SUCCESS, 0:00:18
successfully ran 2 tests
```

The root and unshare transcripts each show:

- both inner `script -c` hooks printing `foobar`;
- no `No such file or directory` match in the copied apt log;
- `/tmp/test.c` and `/tmp/log` removed by the test;
- mmdebstrap temporary root removed after success.

This carrier bundled the unit source hunk into the installed-command patch, which later repository fixture tests rejected as a responsibility violation. The package result itself is positive.

## Run 30690452822

```text
execution head: 55b603aa9a819217c19055a7becc91cf4832f082
artifact ID: 8815724078
artifact name: mmdebstrap-reproduction-gha-30690452822-1
artifact digest: sha256:897189064d42e06367ab652f590eb5827388dce8d883c042f079e49a7662273e
console digest: sha256:d9ec564c256c02717a1de24d7a776e98a57ac104d016363d9f35ebd11d2d5c0f
finished: 2026-08-01T08:10:16Z
autopkgtest wrapper status: 2
testsuite result: PASS
```

Exact candidate application receipt:

```text
patching file tests/dev-ptmx
```

The unit patch was the fifth independent patch carrier and applied with the harness's zero-fuzz/zero-offset contract.

Named results:

```text
(253/284) dev-ptmx --mode=root:    SUCCESS, 0:00:36
(254/284) dev-ptmx --mode=unshare: SUCCESS, 0:00:42
successfully ran 2 tests
```

The root and unshare transcripts each show:

- both inner `script -c` hooks printing `foobar`;
- no missing-command signature;
- `/tmp/test.c` and `/tmp/log` removed;
- temporary roots `/tmp/mmdebstrap.5lTCUZ7pbX` and `/tmp/mmdebstrap.NzHLTKNsNF` removed after success.

## Wrapper-status interpretation

Both autopkgtest invocations returned status `2` because the control file also contains `hint-testsuite-triggers`, which autopkgtest classified as:

```text
hint-testsuite-triggers SKIP unknown restriction hint-testsuite-triggers
testsuite            PASS
```

The selected mmdebstrap testsuite passed. Status `2` belongs to the unrelated skipped control entry and does not change the two named `dev-ptmx` success results.

## Disposition

Current-sid dynamic confirmation is positive twice across two separate disposable containers. Run `30690452822` is the cleaner source-application receipt because the unit patch is independent and exact. A direct one-case carrier in PR `#407` remains useful for a zero-status execution and explicit residual-process/mount checks. Canonical Forgejo byte/history review remains the external-delivery gate.
