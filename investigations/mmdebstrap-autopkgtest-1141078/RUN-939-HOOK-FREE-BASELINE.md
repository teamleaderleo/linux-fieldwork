# CI 939 — hook-free capability case reached; tar baseline missing

State: `carrier-repair-created`

## Exact run

- PR #72 head: `7ff6d07c19c8f84a83b7bcb214ff85b2ea1cb7b7`
- Linux CI: `30633385029` / 939
- reproduction job: `91164883569`
- retained artifact: `8794809068`
- artifact digest: `sha256:3cb9be61e93cd0a75433038e66d51b6f4cabbacf35859e9be6c4af9b8e113916`
- container result: status 6; autopkgtest testsuite status 1
- repository/lab-tools job: passed

## What cleared

The sid carrier passed exact patch validation, Python compilation, repository tests, shell syntax, and command-help checks.

The disposable sid autopkgtest then:

1. installed current sid tooling;
2. applied the installed-command, Deb822 sourcesfilter, hook-free hard-failure, sid signal-compatibility, and integration-order transformations;
3. built the shared mirror/cache;
4. entered the reordered hook-free hard phase;
5. selected `root-without-cap-sys-admin`;
6. executed real `/usr/bin/mmdebstrap` after dropping CAP_SYS_ADMIN.

`mmdebstrap` completed successfully in 7.7627 seconds. The warnings about unavailable mount operations were expected under the dropped capability.

## First failure

After the archive was created, the test ran:

```text
tar -tf /tmp/debian-chroot.tar | sort | diff -u tar1.txt -
```

and failed because `tar1.txt` did not exist.

This is not a capability failure. The imported source makes the dependency explicit:

- `tests/create-directory` creates `tar1.txt`;
- `tests/root-without-cap-sys-admin` consumes `tar1.txt`.

Historically, the broad matrix ran `create-directory` before the capability case. The integration-only carrier deliberately moved the hard hook-free phase ahead of the broad matrix so an unrelated earlier failure could not hide it, but did not carry its fixture producer with it.

## Selected repair

Keep the selected phase order:

```text
hook-free hard > broad matrix > soft transition
```

Make the hard phase self-contained by prefixing its selected list:

```sh
HOOK_FREE_HARD_TESTS="create-directory $HOOK_FREE_HARD_TESTS"
```

Both tests then run under the same hook-free `CMD=mmdebstrap` invocation. Coverage configuration order places `create-directory` before `root-without-cap-sys-admin`. A fixture failure remains a hard package-test failure, as does the target failure.

## Repair carrier

- branch: `repair/72-hook-free-tar-baseline`
- changed patch: `0001-run-hook-free-capability-case-as-hard-failure.patch`
- additive regression: `tests/test_mmdebstrap_hook_free_tar_baseline.py`
- this receipt: `RUN-939-HOOK-FREE-BASELINE.md`

## Boundary

This repair changes only disposable integration scheduling. It does not change imported product source or the capability test. The real sid matrix must run again before any package conclusion.

Internal work only. External contact authorized: `false`.