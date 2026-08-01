# Deep dive

## Question and observed failure

Does Debian mmdebstrap’s package-test setup decide whether `AUTOPKGTEST_NORMAL_USER` already has subordinate UID/GID ranges by comparing the account field literally and exactly?

The current block searches each complete record with:

```sh
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid
grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid
```

For requested user `debci`, the unrelated row `old-debci-helper:200000:65536` returns success. Setup skips `debci:100000:65536`, and later tests that need a user namespace can fail after the actual cause has disappeared from view.

This belongs to the Debian package-test shell. The harness chooses whether to append the records before invoking mmdebstrap coverage. The runtime, mirror, namespace implementation, and package dependency set have no control over this earlier false positive.

## Source mechanism

`debian/tests/testsuite` prepares the ordinary autopkgtest user, temporary mirror, wrapper files, and subordinate-ID records. It then runs `make_mirror.sh` and `coverage.sh` as that ordinary user.

A subordinate-ID record is colon-delimited. Field 1 is the account identity. Searching the full line as a regular expression conflates three properties:

- account identity;
- substring presence elsewhere in an account name or record;
- regular-expression interpretation of the requested username.

The candidate uses:

```sh
cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
cut -s -d: -f1 /etc/subgid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"
```

`cut -s` drops delimiter-free malformed lines, `-F` treats the value literally, `-x` requires complete field equality, `-q` preserves quiet predicate behavior, and `--` protects a leading-hyphen identity.

## Reproduction narrative

The smallest discriminator is one file containing only:

```text
old-debci-helper:200000:65536
```

with `AUTOPKGTEST_NORMAL_USER=debci`.

The baseline predicate succeeds and leaves the file unchanged. The candidate predicate sees field 1 as `old-debci-helper`, finds no exact `debci`, and appends:

```text
debci:100000:65536
```

An immediate second run finds the exact field and leaves the file byte-identical.

## Approach history

### Approach A — unanchored whole-record grep

- mechanism: search the complete record as a regular expression;
- evidence: exact source in issue #80 and PR #92;
- result: false positives for substring accounts and regex-significant values;
- compatibility cost: hidden setup omissions;
- disposition: rejected.

### Approach B — anchored whole-line grep

- mechanism: anchor the username at the start of the record;
- evidence: considered during focused review;
- result: requires careful delimiter and regex escaping, still couples account parsing to grep syntax;
- compatibility cost: malformed rows and regex input remain easy to mishandle;
- disposition: rejected in favor of explicit field parsing.

### Approach C — `cut -d: -f1 | grep -Fxq --`

- mechanism: extract field 1 and compare a fixed whole line;
- evidence: initial PR #92 candidate;
- result: delimiter-free input is emitted unchanged by `cut` and can masquerade as an account row;
- compatibility cost: malformed input suppresses setup;
- disposition: superseded.

### Approach D — `cut -s -d: -f1 | grep -Fxq --`

- mechanism: suppress delimiter-free rows, compare field 1 literally and exactly, terminate options explicitly;
- evidence: repaired PR #92, proof lineage through PR #291, fresh packet-local smoke;
- result: all bounded cases pass with identical subuid/subgid behavior and rerun idempotency;
- compatibility cost: only malformed and false-positive records cease to count as the requested account;
- disposition: selected.

### Approach E — tolerate fuzzy retained patches

- mechanism: allow GNU patch context fuzz;
- evidence: PR #252 gate `30598944690` / 797 found a hunk declaring ten lines while supplying nine;
- result: packaging error surfaced before behavioral execution;
- compatibility cost: approximate application can certify a different source location after drift;
- disposition: rejected; proof requires `--fuzz=0` and no fuzz output.

## Selected correction

Change the two account-presence conditions in `debian/tests/testsuite`. Preserve the existing append strings, setup order, shell control flow, and all later package-test operations.

The upstream-path patch is retained at `patches/0001-debian-tests-match-subid-account-field-exactly.patch`.

## Why the changes belong together

The subuid and subgid conditions implement one invariant for the same ordinary test user and are adjacent in one setup block. One test matrix exercises both. A partial correction would leave asymmetric namespace setup.

## Compatibility analysis

### Content and file effects

- Exact existing account rows remain untouched.
- Missing, empty, substring-only, delimiter-free, and regex-confusable cases receive the same existing `<user>:100000:65536` append.
- Immediate rerun remains byte-identical.
- File paths, modes, owners, timestamps beyond the existing append, and surrounding files remain under the same shell operations.

### Status and output

- The predicates remain quiet.
- Successful setup retains status 0.
- Existing `set -e`/conditional semantics remain.
- No new stdout or stderr is introduced.

### Process and cleanup

- The correction starts no process beyond the existing short `cut` and `grep` pipeline.
- No descriptors, sockets, mounts, namespaces, locks, or background processes are added.
- Packet-local tests use temporary directories and remove them on exit.

### Command lookup and portability

- Debian’s test dependency environment already supplies coreutils `cut` and grep.
- The syntax is POSIX-shell compatible as executed by `/bin/sh` in the retained proof.
- `grep -F`, `-x`, `-q`, and `--` match the GNU grep environment used by the Debian package test.

### Supported identities

- Ordinary account names, regex-significant strings, and leading-hyphen strings are handled literally.
- Numeric subordinate-ID identities are a separate runtime capability and remain outside this package-test account-name correction.

## Negative controls and losing mutations

The baseline substring case is the primary losing control: it returns success and appends nothing.

The retained proof also loses when:

- `cut -s` is removed and a delimiter-free `debci` line is present;
- `-F` is removed and the requested value contains regex syntax;
- `-x` is removed and a field contains the requested value as a substring;
- `--` is removed and the requested value begins with `-`;
- candidate line count differs from baseline;
- the retained patch needs fuzz;
- either subuid or subgid condition remains unchanged.

## Current upstream and historical review

Issue #80 bounded the defect. PR #92 merged the product patch internally after repairing the delimiter-free case. PRs #215, #218, and #225 carried or restacked stronger proof. PR #252 introduced zero-fuzz enforcement and exposed a malformed retained hunk declaration. PR #291 repaired that hunk and merged the durable proof after CI `30624718470` / 845 passed.

Current public refresh found Debian source 1.5.7-3 as the latest published package and a dgit master view at `c8a789205ded12daccfb16deaa35ddd1fc8d688f`. The package-test condition remains represented by the exact Linux Fieldwork imported blob. Upstream runtime commit `6f0a2fcd...` adds numeric UID/GID support in different files and leaves this correction useful.

## Remaining questions

1. **Exact current Salsa head:** direct clone or API output must identify the full `master` commit and the blob for `debian/tests/testsuite`.
2. **Exact-head application:** apply the upstream-path patch with `git apply --check` and zero context drift on that checkout.
3. **Focused integration:** identify and run the shortest Debian package/user-namespace test path that consumes the newly ensured records.
4. **Public overlap:** repeat issue/MR search immediately before any authorization request.
5. **Contributor identity:** replace the internal placeholder author in the formatted patch when a controlled fork/branch is created.

## Evidence boundary

Established evidence covers shell predicate behavior, exact source-line intent, zero-fuzz patch packaging on the retained imported source, full shell syntax on that source, and synthetic file behavior for both subuid and subgid.

The packet has yet to establish a current-Salsa exact-head application, Debian autopkgtest execution, distribution/architecture integration result, or public review acceptance.

## Reopen triggers

- current Debian packaging already contains equivalent field-aware matching;
- `debian/tests/testsuite` moves or changes the account setup owner;
- Debian supports a subordinate-ID record grammar requiring a different parser;
- the ordinary test user can be numeric in this exact package-test environment;
- an active equivalent MR appears;
- explicit external authorization changes the delivery phase.
