# Current upstream fetch attempt — 2026-08-02

## Goal

Resolve the exact current commit of Debian mmdebstrap Salsa branch `master` and retrieve the exact current `tarfilter` bytes before rebasing unit 16.

## Public identity confirmed

- canonical project page: `https://salsa.debian.org/debian/mmdebstrap`
- project ID shown by the public page: `30687`
- intended branch shown by the public page: `master`
- public page advertised 582 commits at the retrieval boundary.

This confirms the destination identity. It does not establish the current branch commit.

## Retrieval attempts

1. Direct GitLab branch API endpoint:

   `https://salsa.debian.org/api/v4/projects/30687/repository/branches/master`

   The available web reader could not retrieve the endpoint directly.

2. Project commit listing:

   `https://salsa.debian.org/debian/mmdebstrap/-/commits/master`

   Following the public project's `Commits` link returned a cache-miss retrieval failure.

3. Raw current source:

   `https://salsa.debian.org/debian/mmdebstrap/-/raw/master/tarfilter`

   The available web reader could not retrieve the raw path directly.

4. Git transport:

   ```sh
   git ls-remote https://salsa.debian.org/debian/mmdebstrap.git refs/heads/master
   ```

   Result:

   ```text
   fatal: unable to access 'https://salsa.debian.org/debian/mmdebstrap.git/': Could not resolve host: salsa.debian.org
   ```

5. Search-engine results exposed the project and release tags through August 2025, but did not expose a trustworthy current `master` commit or current raw `tarfilter` identity.

## Disposition

`BLOCKED BY PUBLIC FETCH PATH IN THIS EXECUTION ENVIRONMENT`

Do not substitute:

- the latest visible release tag;
- a third-party GitHub mirror;
- Debian Sources package bytes;
- an inferred commit from page activity;
- the imported blob already in Linux Fieldwork.

None of those proves the exact current Salsa `master` identity.

## Next safe action

From an environment with working Salsa DNS/HTTPS or an already authenticated/readable GitLab connector:

1. fetch `refs/heads/master` and record the full commit SHA;
2. fetch `tarfilter` at that exact SHA;
3. record its Git blob or SHA-256 identity;
4. compare it byte-for-byte with imported blob `ad776167a8473d5d15dbe22e850f4f6db35cf278`;
5. continue zero-fuzz rebase only after those identities are durable.

External contact remains unauthorized. No fork, issue, merge request, comment, email, or maintainer interaction occurred.
