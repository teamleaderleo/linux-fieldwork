# GitHub fork application receipt

Recorded: `2026-08-01 15:52 +08:00`

## Candidate repository

| Item | Value |
| --- | --- |
| Repository | `teamleaderleo/mmdebstrap` |
| Repository default branch | `master` |
| Candidate branch | `linux-fieldwork/unit-10-subid-exact-match` |
| Base commit | `574048f2a720057b75e56622003932f344dc700a` |
| Candidate commit | `eb75165459760cd4b9d8801147393bbde0535df6` |
| Commit subject | `debian/tests: match subid account fields exactly` |
| Baseline file | `debian/tests/testsuite` |
| Baseline Git blob | `9f4eda87430da38b08a23a50a51e53b22cf7414b` |
| Candidate Git blob | `6925c7f05c3a5f050a4d3f89142085ff687ce3b0` |

## Connector-observed application

The GitHub connector read `debian/tests/testsuite` from fork `master` and returned baseline blob `9f4eda87430da38b08a23a50a51e53b22cf7414b`. This is the exact baseline admitted by the existing full-source gate.

A candidate branch was created from base commit `574048f2a720057b75e56622003932f344dc700a`. The selected two-line correction was committed as `eb75165459760cd4b9d8801147393bbde0535df6`.

GitHub comparison reported:

```text
status: ahead
ahead_by: 1
behind_by: 0
total_commits: 1
file: debian/tests/testsuite
additions: 2
deletions: 2
changes: 4
```

The committed diff is exactly:

```diff
-if [ ! -e /etc/subuid ] || ! grep "$AUTOPKGTEST_NORMAL_USER" /etc/subuid; then
+if [ ! -e /etc/subuid ] || ! cut -s -d: -f1 /etc/subuid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"; then
@@
-if [ ! -e /etc/subgid ] || ! grep "$AUTOPKGTEST_NORMAL_USER" /etc/subgid; then
+if [ ! -e /etc/subgid ] || ! cut -s -d: -f1 /etc/subgid | grep -Fxq -- "$AUTOPKGTEST_NORMAL_USER"; then
```

The resulting GitHub content blob is `6925c7f05c3a5f050a4d3f89142085ff687ce3b0`, identical to the candidate blob from the prior exact imported-source application gate. Therefore the prior complete shell syntax, Git whitespace, exact diff-fence, and 18-case behavior/idempotency results apply byte-for-byte to this fork commit.

## CI and runtime state

GitHub returned no combined status checks for candidate commit `eb75165459760cd4b9d8801147393bbde0535df6`.

A read-only local clone attempt from the execution container failed before repository access because `github.com` did not resolve. This is an execution-environment DNS limitation. It does not affect the connector-observed branch, commit, diff, or blob identities.

## Authority and contact state

The repository was forked by the user. The candidate branch and commit were created inside that user-controlled fork after the user directed work to continue there.

No issue, pull request, merge request, review, comment, reaction, email, or other contact was sent to an upstream maintainer or upstream project.
