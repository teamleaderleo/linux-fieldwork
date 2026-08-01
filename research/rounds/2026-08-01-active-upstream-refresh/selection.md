# Active upstream contribution refresh

Date: `2026-08-01`  
Branch: `research/2026-08-01-active-upstream-refresh`  
External contact: `false`

## Decision

Reduce new investment in `mmdebstrap` after completing the current bounded packet. Its contribution surface is useful for Debian package-test work, while review and maintenance concentration make it a weak primary pipeline.

Use repositories with visible current commits, multiple contributors, active human review, executable tests, and issue queues where overlap can be checked precisely.

## Ranked work

### 1. Continue: systemd OOMD reporter collision

- Upstream: `systemd/systemd#43174`
- Linux Fieldwork: issue `#140`, draft PR `#245`
- Current state: source mechanism confirmed; retained exact-path regression; current-main VM execution and product-policy design remain.
- Why continue: consequential silent guardrail loss, strong reproducer, active multi-reviewer upstream, existing source work, and a precise VM gate.
- Next action: run the retained `TEST-55-OOMD.sh` regression on a current-main VM and preserve the ManagedOOM message sequence. Keep implementation selection behind an explicit effective-policy decision for overlapping reporters.

This is continuation work rather than a fresh candidate.

### 2. Start: libarchive cpio large-inode test and mapping correctness

- Upstream: `libarchive/libarchive#3314`
- State on refresh: open, unassigned, no matching pull request found.
- Maintainer direction: a pull request is explicitly welcome. Tests should prove that in-range inode values remain correct and out-of-range values receive unique in-range archive values.
- Reporter state: reporter lacks bandwidth and uses a downstream tmpfs workaround.
- Likely boundary:
  - `cpio/test/test_format_newc.c`
  - `cpio/test/test_option_c.c`
  - cpio inode-number assignment/mapping code
- First discriminator:
  1. make the tests deterministic without relying on the host filesystem allocating a huge inode;
  2. establish current behavior for in-range, colliding truncated, and out-of-range inode values;
  3. decide whether the defect belongs only to test expectations or to archive inode synthesis;
  4. require uniqueness after representational narrowing.
- Promotion signal: one bounded product correction plus regression coverage on ordinary Linux CI.

This is the best fresh candidate from the refresh.

### 3. Scan pool: BuildKit beginner and UX queue

- Repository: `moby/buildkit`
- Strength: high current development and a maintained `exp/beginner` queue.
- Constraint: overlap changes quickly. Issue `#6963` looked current and bounded but already has PR `#6972`, so independent work stops.
- Older issue `#2396` is still open, though maintainer guidance says undeclared `ARG` is valid and the desired behavior needs design rather than a simple error check.
- Next action: repeat a narrow overlap scan before selecting any BuildKit item; prefer a recent issue with a direct test owner and no open PR.

### 4. Watch: util-linux agetty redraw regression

- Upstream: `util-linux/util-linux#4306`
- Technical signal: maintainers identified the `\\t` plus netlink-monitoring interaction and discussed two-pass parsing/network-monitor selection.
- Overlap: the reporter published an active draft comparison branch. Treat the lane as occupied until that work is retired or maintainers request another implementation.

## Explicit exclusions

| Candidate | Reason excluded from fresh implementation |
| --- | --- |
| libarchive PPMd short-read issue `#3337` | active equivalent PR `#3340` |
| libarchive standalone AppleDouble issue `#3310` | active equivalent PR `#3334` |
| systemd bind-path whitespace issue `#43214` | active equivalent PR `#43217` |
| systemd ephemeral-root ownership issue `#43232` | active equivalent PR `#43233` |
| BuildKit git-advice issue `#6963` | active equivalent PR `#6972` |
| util-linux agetty issue `#4306` | reporter has an active draft implementation branch |

## Repository-health conclusion

`systemd`, `libarchive`, `util-linux`, and BuildKit all show current substantive work and review traffic. `systemd` is the strongest deep-investigation target. `libarchive` currently offers the cleanest fresh bounded contribution. BuildKit is the strongest recurring beginner scan pool. util-linux has worthwhile work, though the current candidate already has an implementation owner.

## Immediate execution order

1. inspect the current `teamleaderleo/libarchive` fork at exact source identity;
2. locate the two failing cpio tests and inode assignment owner;
3. construct a deterministic narrow-range fixture before selecting a fix;
4. keep systemd PR `#245` queued for its VM gate;
5. perform no upstream contact or claim without explicit authorization.

## Authority

Public source, issues, pull requests, and review traffic were read. This branch records internal research only. No upstream issue comment, pull request, review, reaction, email, or other contact was created.