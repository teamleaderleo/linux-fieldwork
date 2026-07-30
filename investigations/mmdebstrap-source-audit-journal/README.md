# mmdebstrap source-audit journal — 2026-07-30

## In simple words

This record collects the source defects, candidate fixes, duplicate cleanup, review findings, and evidence limits discovered while extending Linux Fieldwork beyond the original scout assignments. The strongest results are in `tarfilter`: valid archives can be corrupted, path filters can select the wrong members, transforms diverge from GNU tar, and invalid option values can silently rewrite paths. A separate process-lifecycle defect allows a parent-only termination signal to be logged and then reported as success.

The purpose of this journal is coordination, not replacement of the focused investigations. Canonical issue, investigation, test, and pull-request records remain the source of detailed evidence.

## Identity and coordination

- Recording scout: `LF-SCOUT-DEB-02`
- Home lane: `LF-12`
- Round coordination: issue #10
- Original assignment: issue #15 / PR #19
- Source-audit work crossed LF-14, LF-23, and LF-02 boundaries after the LF-12 probe reached a retained `stop` result.
- No external issue, email, merge request, patch, comment, or review was created.

## Source boundary

- Project: imported `mmdebstrap`
- Imported package/revision: Debian `1.5.7-3`
- Imported source commit recorded by the repository: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Primary files read:
  - `upstream/mmdebstrap/tarfilter`
  - `upstream/mmdebstrap/mmdebstrap`
- Primary reference implementations:
  - GNU tar `--transform`, sparse archive listing, and extraction behavior
  - Python `tarfile`, `argparse`, `fnmatch`, and `re` behavior used by the imported implementation

## Findings and current disposition

### No-option archive passthrough

The intended byte-copy branch is unreachable because `argparse` always creates `strip_components`. A nominal no-op therefore parses and re-emits the archive, exposing inputs to format loss and the sparse corruption path.

- Canonical issue: #29
- Duplicate closed: #27
- Investigation: `investigations/tarfilter-no-option-passthrough/README.md`
- Candidate stack: PR #33
- Regression: byte identity for no options and explicit no-op values, including composition with the sparse repair

### Path-filter normalization and parent retention

`member.name.lstrip("./")` aliases dotfiles with non-dot names and can erase traversal components during matching. Parent-retention logic also derives a prefix from `fnmatch.translate()` output rather than the original glob. The first local correction handled exact nested includes but remained incomplete for wildcard includes such as `/foo/*/bar`; a later negative regression caught and corrected that gap.

- Canonical issues: #38 and #39
- Combined duplicate closed: #28
- Investigation: `investigations/tarfilter-path-filter-matching/README.md`
- Candidate stack: PR #33
- Exact-head CI receipt: run `30535373218`, success

### Sparse archive rewriting

The imported filter can combine expanded logical payload data with stale GNU sparse metadata, producing invalid output. The local repair normalizes output to GNU PAX sparse 1.0 or a valid dense fallback. Old GNU sparse type `S` requires an additional normalization to a regular-file member before either output form.

- Base sparse evidence: PR #17
- Main repair candidate: PR #23
- Old-GNU type completion: issue #44 / PR #45
- Regression boundary: content equality, extraction, logical size, sparse allocation, compact archive size, regular output type, and dense fallback

### Transform substitution language

The imported transform loop calls Python `regex.sub()` without a count, so every match is replaced even though GNU tar defaults to the first match. Explicit `g` is rejected. Replacement-string semantics and transform target scopes also differ from GNU tar.

- Broader canonical issue: #36
- Focused first/global issue: #51
- Symlink-target scope follow-up: #62
- Investigation: `investigations/tarfilter-transform-semantics/README.md`
- Candidate stacks: PR #52 and the more focused retained transform work linked by the investigation
- Corrected behaviors include first-only default, `g`/`i`, replacement `&` handling, and GNU `r/R`, `s/S`, and `h/H` scopes
- Exact-head CI receipt for the expanded local stack: run `30535637452`, success

### Hard-link and PAX reference metadata

Member renames must update hard-link targets and remove stale PAX `path`/`linkpath` records. PR #48 repaired those cases, but its merged regression retained an incorrect rule for default symlink-target transforms. Issue #62 records that integration gap; the expanded transform candidate corrects it by following GNU tar's default `rsh` scope and using `S` as the symlink opt-out.

- Canonical issue: #25
- Merged local candidate: PR #48
- Follow-up integration issue: #62

### Negative strip-components

Negative values are accepted as Python slice indexes. Instead of failing, `--strip-components=-1` keeps only the final component and `-2` keeps the final two components. GNU tar rejects negative values.

- Canonical issue: #58
- Candidate stack: PR #59
- Exact-head CI receipt: run `30535717481`, success
- Severity: low–medium; explicit invalid input is required, but silent layout rewriting is worse than a clear failure

### Parent-only cancellation

`run_progress()` installs signal handlers that log parent-only `INT`, `HUP`, `PIPE`, and `TERM`, but the handler does not set the later `got_signal` state. After the child exits successfully, the owner can return success despite having received a termination signal.

- Canonical issue: #30
- Candidate: PR #34
- Candidate records the first signal, finishes child cleanup, and then follows the existing nonzero error path

### Chrootless host configuration and host mutation

The imported source itself warns that host dpkg configuration is parsed and can affect chrootless installation. Controlled work reproduced a host `needrestart` logger and host `/run` mutation. This is a real containment concern, but the obvious command-line mitigation is insufficient because several dpkg options are additive and cannot reliably erase hostile host configuration.

- Scout work: issue #11 / PRs #21 and #22
- Related Debian boundary: bug #1038404
- Current disposition: retain as an architectural limitation requiring a dpkg-supported configuration namespace or equivalent isolation mechanism; do not claim a safe one-line fix

## Review work

### LF-02 host-containment review

The host `needrestart` mutation is a real behavior. APT shutdown inhibition and general environment inheritance are not independently proven defects because they are intentional or documented surfaces unless a narrower containment contract is established.

### PR #48 review

The hard-link and stale-PAX fix was valid. The default symlink expectation was not: GNU tar transforms symlink targets by default. A review requested a default transformed-target case and an explicit `S` opt-out case. The final merged record still retained the wrong expectation, so issue #62 and the expanded transform candidate preserve the correction.

### Harness-versus-product discipline

Several reviews found malformed retained patches or tests that failed before product code executed. Those were recorded as harness/package-carrier failures, not product evidence. CI failures were not promoted into source claims until the candidate patch applied and the negative control plus repaired behavior both executed.

## Duplicate cleanup

- #27 closed as duplicate of #29
- #28 closed as an aggregation duplicate of #38 and #39
- #51 retained as a focused transform issue while #36 remains the broader canonical mismatch

Linking focused records is preferable to carrying multiple independent descriptions of the same source defect.

## Evidence limits

- Most archive regressions run on Ubuntu 24.04 hosted CI with GNU tar as the differential reference.
- The imported source remains unchanged; candidates are retained as patches applied to exact temporary copies.
- Complete compatibility with every tar implementation, sed/BRE feature, sparse dialect, Python version, or archive extension is not established.
- The chrootless host-configuration problem has a confirmed mechanism and mutation, but no validated general isolation fix.
- These records do not authorize upstream contact.

## Next steps

1. Keep stacked candidates composable and test exact heads after base changes.
2. Review active LF-02 and LF-14 work for product behavior, not only harness quality.
3. Continue source reading for small defects with a reference implementation or a strong invariant.
4. Consolidate accepted fixes into fewer upstream-ready patches only after explicit authorization.

## Authority

All work remains inside `teamleaderleo/linux-fieldwork`. No upstream contact is authorized or made.