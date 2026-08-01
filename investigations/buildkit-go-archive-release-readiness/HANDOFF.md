# Handoff — BuildKit / go-archive release readiness

State: `ACTIVE — EXECUTION PENDING`  
Linux Fieldwork branch: `research/hot-repos-2026-08-01`  
External contact authorized: `false`  
External contact made: `none`

## Completed

- read Linux Fieldwork project, coordination, fieldwork, target, and programme instructions;
- refreshed active upstream repositories and recent issue/PR state;
- checked Linux Fieldwork overlap for the shortlisted candidates;
- retained libarchive AppleDouble PR #3334 as an active-fix reference;
- selected BuildKit/go-archive release readiness as the highest-value current-CI investigation;
- pinned BuildKit rollback and go-archive repair identities;
- defined the four-candidate dependency matrix, negative controls, metadata checks, containment checks, performance boundary, cleanup requirements, and stop rules;
- recorded libarchive RAR5 #3300 as the next direct implementation candidate;
- made no upstream contact.

## Exact source identities to refresh before execution

- BuildKit rollback merge: `275d6864ff0ce91a06225af5f5b012887bd257cf`
- BuildKit test head: `22ea4efb43c3c91651dab7f44d1599c4c42b9412`
- user's observed BuildKit fork head: `df0761886a20e368d75e0aa6bb3f20874f58b692`
- go-archive implied-parent merge: `279fa6d455e5a39d8e24e67dd236abee6e2de08b`
- go-archive absolute-symlink/hard-link merge: `9e6d2c7c969f4871fe6ded98ae0e28963fde311f`

## First incomplete step

Create clean local BuildKit and go-archive checkouts, confirm the current upstream heads, and run the rollback's focused integration tests against:

1. go-archive v0.2.0;
2. go-archive v0.2.1;
3. go-archive v0.3.0;
4. go-archive current `main`.

Record the exact Go version, kernel, filesystem, test package/selectors, command outputs, statuses, tree and inode checks, timing/syscall evidence, cleanup, and immediate rerun.

## First command sequence

```sh
git clone https://github.com/teamleaderleo/buildkit.git buildkit-go-archive-readiness
cd buildkit-go-archive-readiness
git remote add upstream https://github.com/moby/buildkit.git
git fetch upstream
git checkout --detach 275d6864ff0ce91a06225af5f5b012887bd257cf

git clone https://github.com/moby/go-archive.git ../go-archive-candidate
cd ../go-archive-candidate
git checkout 9e6d2c7c969f4871fe6ded98ae0e28963fde311f
go test ./...
```

Return to BuildKit, replace the dependency with the absolute candidate path, identify the exact package selector for the two new Dockerfile ADD tests, and run them. Do not treat an invalid Go test selector or missing integration backend as a product failure.

## Stop conditions

- equivalent active BuildKit dependency-bump work appears;
- the defining integration sandbox is unavailable;
- the first red result belongs to stale source, module selection, toolchain, or fixture setup;
- containment negative controls weaken;
- cleanup cannot prove no retained process, mount, socket, trace, temporary tree, or module mutation.

## Next candidate if blocked

Open a refreshed branch from `libarchive/libarchive` current `master` for issue #3300. Add the smallest normal/overlong RAR5 fixture and prove exact byte consumption before changing `read_var()`.

## Read first

1. `README.md`
2. `../../research/rounds/2026-08-01-hot-repository-refresh/selection.md`
3. BuildKit PR #7005
4. go-archive PRs #92 and #93

## Authority

Internal fork synchronization, branches, tests, benchmarks, and evidence records are allowed. No public issue, pull request, comment, review, or email is authorized.
