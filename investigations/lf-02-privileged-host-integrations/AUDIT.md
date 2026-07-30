# LF-02 expanded-evidence post-run audit

## In simple words

The expanded LF-02 run still proves the important result: under a privileged caller, the host `needrestart` logger created `/run/needrestart/unpacked`, APT acquired a host shutdown inhibitor, and the two controls removed those host integrations independently.

A post-run audit found **one confirmed correctness bug in a raw machine-readable field** and several lower-severity evidence-quality or coverage improvements. The bug can falsely say that logind denied access when the trace only contains an unrelated `Permission denied`. It did **not** participate in the workflow pass/fail gate, it is absent from the retained hand-curated `results/summary.json`, and it does not change the LF-02 `promote` decision.

This is not seven equally serious bugs. The audit classifies one item as medium severity, two as low-severity evidence-quality work, and the remaining items as informational scope or maintainability notes.

## Question

Does the expanded LF-02 evidence generator and report describe its observations accurately enough to support the retained conclusions, and which follow-ups are defects versus ordinary evidence limits?

## Source

- Repository: `teamleaderleo/linux-fieldwork`
- Investigation: `investigations/lf-02-privileged-host-integrations/`
- Audited branch: `investigation/lf-02-privileged-host-integrations`
- Audited head before this note: `c2d361a362c9244085dbb9a7aa299da527e782a7`
- Imported mmdebstrap source: `debian/1.5.7-3`, resolved commit `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Workflow run: `30530666222`
- Job: `90831976076`
- Artifact: `8754537765`
- Artifact digest: `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b`
- Main generator: `run.sh`
- Durable interpretation: `RESULT.md`

## Environment

- GitHub-hosted Ubuntu 24.04 runner
- Root execution through the dedicated workflow
- Three fresh chrootless targets: `default-root`, `no-inhibit-root`, and `isolated-root`
- Local dependency-free package fixture
- `strace -ff -qq -s 4096 -yy -e trace=%file,%process,%network`
- No real credentials or external upstream interaction

## Reproduction and source trace

The generator first collects a broad result file:

```sh
grep -hE 'SCM_RIGHTS|AccessDenied|Permission denied' "$result_dir/$label.trace"* \
    > "$result_dir/$label-dbus-result.txt" || true
```

It then derives:

```python
"logind_access_denied": (
    "AccessDenied" in dbus_result
    or "Permission denied" in dbus_result
),
```

The `dbus-result` file is not scoped to the logind D-Bus exchange. Any unrelated syscall text containing `Permission denied` satisfies the second condition.

In the retained artifact:

- `no-inhibit-root-logind-messages.txt` is empty;
- `isolated-root-logind-messages.txt` is empty;
- both cases have no system-bus connection;
- their broad `dbus-result` files still contain unrelated permission errors;
- the raw generated summary can therefore report `logind_access_denied: true` for cases in which no logind call occurred;
- `default-root` received an inhibitor file descriptor through `SCM_RIGHTS`, so a simultaneous generic “access denied” conclusion would also be contradictory without a message-correlated D-Bus error.

The workflow success expression does not read `logind_access_denied`, and the committed `results/summary.json` omits that field.

## Results and severity

| ID | Classification | Severity | Finding | Effect on retained LF-02 conclusion |
|---|---|---|---|---|
| `F-01` | confirmed generator correctness bug | **medium** | `logind_access_denied` treats any generic `Permission denied` in a broad trace extract as a logind denial, including controls with no D-Bus/logind call | none; the field is not part of the pass gate or retained summary, but raw consumers can be misled |
| `F-02` | evidence semantics improvement | **low** | equality assertions cover normalized maintainer-script output and alternatives state only; full target trees are captured but not asserted equal | none; `RESULT.md` correctly names the two compared projections, but machine consumers should not generalize them to whole-tree equality |
| `F-03` | provenance improvement | **low** | raw environment capture records the commit but not all workflow/ref metadata and emits runner-specific absolute paths | none; `RESULT.md` separately records branch, run, job, artifact, and digest |
| `F-04` | scope limit, not a bug | **informational** | the local package has no dependencies and the custom run uses an empty suite/source boundary, so dependency resolution is not exercised | none inside the declared dependency-free fixture boundary |
| `F-05` | scope limit, not a bug | **informational** | the fixture does not cover upgrade, conffiles, triggers, dependencies, multiarch, failed scripts, or split unpack/configure behavior | none; this limits generalization to other package lifecycles |
| `F-06` | measurement note, not a bug | **informational** | repeated-run timing and raw trace counts can vary with warm caches and scheduler state | none; timing and event count are not workflow correctness invariants |
| `F-07` | maintainability improvement | **low** | the JSON has no schema version and uses ad hoc field/value shapes that are awkward for long-lived consumers | none for the current human-readable report |

## Interpretation

### Confirmed bug

`F-01` is a real evidence-generation defect. It is medium rather than high severity because it can produce a false machine-readable conclusion about logind behavior, but it does not change the observed successful host mutation, inhibitor acquisition, control behavior, cleanup, or final promotion decision.

### Low-severity items

`F-02`, `F-03`, and `F-07` are evidence-quality and maintenance risks. They can make future automation or later readers overgeneralize or lose provenance, but they do not currently falsify the central result.

### Informational items

`F-04`, `F-05`, and `F-06` are not defects in the tested claim. They describe what the small fixture and two-run design do not establish. They should be written down so later work does not accidentally present this probe as a comprehensive package-manager conformance suite.

## Evidence boundary

- The raw `logind_access_denied` contradiction was observed in the workflow artifact and explained directly by the generator source.
- This audit did not rerun the workflow with a corrected parser.
- The audit does not challenge the raw `execve`, host marker creation, D-Bus `Inhibit` message, `SCM_RIGHTS` reply, control removal, or cleanup evidence.
- The audit does not make a security-severity claim; these ratings are for correctness and evidence quality inside Linux Fieldwork.
- Whole-tree differences may include expected control-specific APT configuration such as `etc/apt/apt.conf.d/99mmdebstrap`; the existing report only claims normalized script and alternatives equality.

## Next step

1. Replace the generic permission-text heuristic with a message-correlated D-Bus result check. At minimum, only evaluate denial when the case has a logind `Inhibit` message and match an actual D-Bus error name such as `org.freedesktop.DBus.Error.AccessDenied`.
2. Add negative controls containing unrelated `EACCES`/`Permission denied` lines and cases with no system-bus connection.
3. Rename or document equality fields as projections, and optionally add a normalized full-tree diff/hash with an explicit allowlist for control-specific files.
4. Record `GITHUB_REF`, `GITHUB_HEAD_REF`, `GITHUB_SHA`, run ID, run attempt, and normalized work-directory placeholders in raw metadata.
5. Add a schema version before another tool consumes the JSON as an API.
6. Keep dependency resolution and wider package lifecycle cases as separate follow-up probes rather than retroactively broadening this one.
7. Rerun the dedicated workflow and replace the raw artifact before citing `logind_access_denied` as evidence.

## Authority

This audit is internal to `teamleaderleo/linux-fieldwork`. No Debian, Ubuntu, mmdebstrap, APT, dpkg, systemd, needrestart, or other upstream issue, email, merge request, patch, comment, or review was created or authorized by this note.
