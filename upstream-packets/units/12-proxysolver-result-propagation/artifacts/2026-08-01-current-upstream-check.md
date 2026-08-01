# Current-upstream corroboration — 2026-08-01

## Purpose

Refresh the current public source and overlap facts for issue #397 unit 12 without contacting upstream or changing any upstream resource.

## Canonical repository observation

Observed through the public canonical repository page:

- repository: `https://gitlab.mister-muffin.de/josch/mmdebstrap`;
- branch: `main`;
- displayed head: `77ec9be5417ee44c96343d2347145585da1b1f94` (`Take hurdfiles on hurd-amd64 as well`);
- displayed repository count: 1,185 commits, 2 branches, 52 tags;
- displayed `proxysolver` last-change record: `add my name to several scripts`, 2021-09-16;
- displayed open issue count: 6;
- the visible open-issue list contains no proxysolver result-propagation report.

This refresh agrees with the identities recorded in the packet on 2026-07-31.

## Debian source corroboration

Observed through Debian Sources and Debian package pages:

- current forky/sid source version: `mmdebstrap 1.5.7-3`;
- `proxysolver` is present at repository root;
- displayed file size: 1,643 bytes;
- Debian Sources lists the same project test entry points (`coverage.py`, `coverage.sh`, and `tests/`).

The Linux Fieldwork imported source is also 1,643 bytes and has Git blob `5cd51fab89104d30b8b12bff18a49d38d9be0003`. Matching size and unchanged history strongly corroborate identity, but they do not replace a byte-for-byte comparison.

## Exact retrieval attempts

### Canonical git transport

Command:

```text
git ls-remote https://gitlab.mister-muffin.de/josch/mmdebstrap.git refs/heads/main
```

Result:

```text
fatal: unable to access 'https://gitlab.mister-muffin.de/josch/mmdebstrap.git/': Could not resolve host: gitlab.mister-muffin.de
```

Classification: execution-environment DNS/network failure before repository access.

### Public raw/archive retrieval

The public web reader reached the canonical repository and Debian Sources listings. Attempts to fetch the canonical raw `proxysolver`, canonical source archive, and Debian Sources file page returned cache-miss or safe-URL retrieval errors before file bytes were delivered.

Classification: retrieval-tool boundary; no source or patch behavior executed.

## Overlap result

No equivalent proxysolver result-propagation issue or pull request appeared in the canonical public repository views available during this refresh. A complete authenticated Forgejo code/issue/PR search remains part of the final current-upstream gate.

## Conclusion

Current public metadata continues to support the selected source and destination. The exact gate remains open:

1. materialize canonical `main` commit `77ec9be5417ee44c96343d2347145585da1b1f94` in a network-enabled environment;
2. verify `git hash-object proxysolver` equals `5cd51fab89104d30b8b12bff18a49d38d9be0003`;
3. apply `patches/0001-proxysolver-propagate-solver-results.patch` without fuzz or offsets;
4. run the packet regression from that checkout;
5. select and run the smallest upstream-native gate.

External-contact state: unauthorized; no upstream contact occurred.
