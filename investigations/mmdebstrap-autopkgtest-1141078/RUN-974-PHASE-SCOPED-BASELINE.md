# Run 974: focused capability passes, broad baseline is phase-stale

State: `true product commands; integration fixture-scope failure`

## Exact identity

- PR: #72
- exact head: `fe84899d7c4de599038c41ad13810b82f832baf6`
- workflow: `30636627420` / 974
- tested generated merge: `87cbe48e7093f0307ef2db83fa12c8edf77b3fd0`
- package artifact: `8796132761`
- artifact digest: `sha256:8e0ab36d6938c5eb676cd8f1550dec978743c3e12d4da4c6b862602c5f407227`
- console digest: `sha256:edf79a9020603460d24bd1e946952542620be1c3b8a56dec9b849064cc76e4a7`
- package exit status: 6
- external contact: unauthorized and none

## Carrier result

The carrier gate passed before package execution:

- four retained patch files;
- nine validated hunks;
- zero fuzz and zero offset;
- 380 retained repository tests passed;
- Python compilation, shell syntax, and command-help checks passed.

This run owns product-level evidence.

## Focused hook-free result

The selector executed the exact producer-consumer pair:

```text
(30/284) create-directory                 SUCCESS
(41/284) root-without-cap-sys-admin       SUCCESS
```

`root-without-cap-sys-admin` completed `/usr/bin/mmdebstrap` after dropping `CAP_SYS_ADMIN`, created the archive, and matched the hook-free `tar1.txt` baseline.

This clears the missing-prerequisite defect from run 939 for the exact run-974 carrier.

## Broad result

The broad host-hook phase then began:

- `help`: success;
- `man`: success;
- `version`: success;
- `create-directory`: skipped because it carried `Needs-Hook-Free-APT-Config`;
- `unshare-as-root-user`: mmdebstrap command success, archive comparison failure.

The broad archive contained these additional host-hook files relative to the retained hook-free baseline:

```text
./etc/apt/preferences.d/90autopkgtest
./etc/apt/sources.list.d/autopkgtest.list
./etc/apt/sources.list.d/debian.sources
```

The product command succeeded. The comparison failed because `tar1.txt` encoded the hook-free phase while the consumer executed with `sourcesfilter` and `file-mirror-automount` hooks.

## Interpretation

`tar1.txt` is a phase-scoped persistent fixture. The hook-free phase needs `create-directory` as an explicit prerequisite, while the broad phase needs to execute `create-directory` again to regenerate a host-hook baseline.

This is not an mmdebstrap product failure.

SIGINT and later broad cases did not run.

## Repair

- keep `Needs-Hook-Free-APT-Config` only on `root-without-cap-sys-admin`;
- prepend `create-directory` explicitly to the hook-free consumer selector;
- allow broad coverage to run `create-directory` normally;
- preserve exact producer-before-consumer ordering and hard status handling.

Issue #357 owns the bounded phase-scoped fixture investigation.

## Evidence boundary

This receipt proves both focused package commands passed and identifies the next integration-fixture failure. It does not establish SIGINT behavior, broad-suite success, or external policy.
