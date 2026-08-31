# Agent Instructions

Treat the owning issue or pull request and the current repository state as the durable assignment. Read [`README.md`](README.md), then route to the owner needed for the task:

- work type and evidence records: [`START_HERE.md`](START_HERE.md);
- collaboration, checkpoints, recovery, review, and third-party GitHub reference hygiene: [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md);
- investigation heuristics: [`FIELD_GUIDE.md`](FIELD_GUIDE.md) and [`BUG_LENSES.md`](BUG_LENSES.md);
- human-designated upstream candidates: [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) and [`CONTRIBUTOR_IDENTITY.md`](CONTRIBUTOR_IDENTITY.md);
- disclosure-sensitive findings: [`SECURITY_RECONVENE.md`](SECURITY_RECONVENE.md).

## Owned-repository research authority

The human owner explicitly authorizes broad autonomous research in repositories and forks owned by `teamleaderleo`. Unless a later human instruction narrows or revokes this authority, agents may create, edit, delete, commit, and iterate on code, tests, instrumentation, branches, fixtures, documentation, CI jobs, and GitHub Actions workflows when that advances the current investigation.

Internal research may be messy. Temporary commits, diagnostic instrumentation, generated material, disposable workflows, carrier branches, failed experiments, and throwaway fixtures are valid execution machinery. Prefer the simplest route that produces evidence; a disposable Actions job is a valid harness for a useful architecture, dependency set, clean environment, or reproducible runtime. Separate harness failures from product failures and preserve useful receipts.

Ordinary internal file edits, commits, branches, test runs, workflow changes, and Actions experiments covered by this authority require no per-step human confirmation. When one normal route is blocked, use another controlled repository or Actions route.

## Third-party and upstream boundary

Owned-repository authority does not publish upstream. Do not open, edit, comment on, review, react to, or otherwise contact a third-party upstream unless the human has authorized that interaction. Avoid accidental GitHub backlinks and follow the canonical redirect rule in [`ADAPTIVE_COORDINATION.md`](ADAPTIVE_COORDINATION.md#external-github-backlinks).

When the human says `upstream greenlight`, treat that natural-language phrase as explicit authorization for the current upstream repository and interaction that is reasonably clear from the conversation; capitalization and an exact template are unnecessary. Ask only when the repository or action is genuinely ambiguous or materially broader than the surrounding context. A greenlight covers that interaction alone; merge, release, deployment, credentials, spending, private-data access, and unrelated actions remain separate. A later human instruction may narrow or revoke it.

## Upstream candidates

A human may designate a specific owned-fork branch or commit series as an **upstream candidate**. From that designation onward, [`SOURCE_BRANCH_HYGIENE.md`](SOURCE_BRANCH_HYGIENE.md) is mandatory for candidate cleanliness, history, base comparison, commit-message policy, and live upstream-PR heads. [`CONTRIBUTOR_IDENTITY.md`](CONTRIBUTOR_IDENTITY.md) owns contributor identity and sign-off provenance.

Internal research branches remain free to use temporary execution machinery; the designated candidate must satisfy its stricter owner before human review or upstream publication. Candidate preparation itself grants no upstream-contact authority.
