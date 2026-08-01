# Exact imported-source application gate — 2026-08-01

State: `PASS`  
Authority: internal read/test work only; no external contact

## Purpose

Replace the earlier reconstructed-nine-line smoke with an exact full-file application gate over the recorded imported Debian `mmdebstrap 1.5.7-3` testsuite blob.

The source file was reconstructed byte-for-byte from the connected Linux Fieldwork repository and admitted only after its Git blob identity matched the durable source record.

## Exact inputs

| Item | Identity |
| --- | --- |
| Source path | `upstream/mmdebstrap/debian/tests/testsuite` |
| Expected source Git blob | `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Observed source Git blob | `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Source SHA-256 | `14bd64347e58cdc36e3b33aaff8663f9ea34dd0ea24049a7452c849923bd090f` |
| Source line count | `219` |
| Packet patch | `patches/0001-debian-tests-match-subid-account-field-exactly.patch` |
| Patch SHA-256 | `fc9c0c4d0552a80565a49a05f068934b3230b81703c9e0ed9c59d3307f9d544d` |

## Exact application gate

Commands:

```sh
git hash-object debian/tests/testsuite
git apply --check --whitespace=error-all 0001.patch
git am --keep-cr 0001.patch
/bin/sh -n debian/tests/testsuite
git diff --check HEAD^ HEAD
git diff --numstat HEAD^ HEAD -- debian/tests/testsuite
```

Observed receipt:

```text
BLOB=9f4eda87430da38b08a23a50a51e53b22cf7414b
Applying: debian/tests: match subid account fields exactly
NEW_BLOB=6925c7f05c3a5f050a4d3f89142085ff687ce3b0
DIFF_STAT= debian/tests/testsuite | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
DIFF_CHECK=
GIT_DIFF_NUMSTAT=2  2  debian/tests/testsuite
```

Candidate identities:

| Item | Identity |
| --- | --- |
| Candidate testsuite Git blob | `6925c7f05c3a5f050a4d3f89142085ff687ce3b0` |
| Candidate testsuite SHA-256 | `d9792e1fa95d4565a49cbe6fcf305d210d0f855a7334049f2f6b366839dc734d` |
| Candidate line count | `219` |
| Ephemeral verification commit | `7af87bd53b84c2c4310e0b58bbce37654748c266` |

The ephemeral commit exists only inside the disposable verification repository. It is evidence, not an upstream candidate head.

## Exact behavior matrix

The matrix read the baseline from `HEAD^:debian/tests/testsuite` and the candidate from the applied working tree. It extracted the real subuid and subgid shell blocks and executed them with temporary stand-in files.

Per path, it covered:

- baseline substring false positive;
- exact account present;
- substring-only account;
- delimiter-free malformed row;
- regex-significant literal account;
- leading-hyphen account;
- empty file;
- absent file;
- immediate rerun byte identity.

Receipt, executed twice:

```text
DIFFS=2
CASES=18
MATRIX=PASS
DIFFS=2
CASES=18
MATRIX=PASS
```

## Cleanup

The disposable repository lived at `/tmp/unit10-exact-source`. The matrix used `TemporaryDirectory` paths for every subuid/subgid stand-in and left no accounts, subordinate-ID records, namespaces, mounts, sockets, packages, cache entries, or background processes.

The temporary verification tree is intentionally outside the Linux Fieldwork repository. Only this compact receipt is retained.

## Interpretation

Established by this gate:

- the full recorded imported source bytes match their claimed Git blob;
- the packet patch applies under Git's whitespace-error gate;
- mail-patch application succeeds;
- the complete candidate shell parses;
- the candidate changes exactly two lines with no line-count drift;
- the complete bounded account matrix passes twice on the exact imported source.

Still outside this gate:

- direct live Salsa `master` SHA and blob verification;
- application against source changes newer than the recorded imported Debian 1.5.7-3 blob;
- Debian package build, autopkgtest, mirror preparation, and user-namespace integration;
- fork, branch, merge request, or any other external action.
