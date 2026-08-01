# Dpkg configuration isolation deep dive

State: `SEPARATE HOLD — confirmed boundary, correction policy unresolved`  
Parent packet: unit 06 chrootless maintainer-script boundary  
External contact authorized: `false`

## Result

The four-patch unit-06 series blocks direct caller-environment inheritance, gives package scripts a target-local `TMPDIR`, selects apt's configured `DPkg::Path`, and invokes the sanitizer through `/usr/bin/env`. It does **not** isolate the host dpkg configuration files read by the dpkg process itself.

That distinction is executable, not hypothetical:

- clearing the environment removes `HOME`, so dpkg stops loading the user-specific `~/.dpkg.cfg`;
- dpkg still loads `/etc/dpkg/dpkg.cfg.d/*` and `/etc/dpkg/dpkg.cfg`;
- system-configured `pre-invoke`, `post-invoke`, and `status-logger` commands execute under the scrubbed environment;
- adding replacement command-line hooks does not remove the configured commands;
- a second status logger that exits immediately can close the status pipe and make dpkg terminate with status `141` while the original configured logger has already run;
- a final `--path-include='*'` neutralized the controlled path exclusion in the retained probe;
- a final target-local `--log=...` selected the target log instead of the configured log;
- the temporary system fragment was removed and its absence was verified before the probe exited.

Exact runner: `scripts/run-dpkg-config-probe.sh`  
Exact receipt: `artifacts/dpkg-config-probe.txt`

Runner SHA-256:

```text
f5c73af6112006f79eb738438143deb4776a741aefac17d5850c0b6da0337edc
```

Receipt SHA-256:

```text
ebc5df68f37350ea973fb5dbec39875cf1578a27dad88fa6dca2f1a2b72ebf76
```

## Prior real-package evidence

LF-02 already demonstrated the production form of this boundary on mmdebstrap `1.5.7-3`:

- Ubuntu's host `/usr/lib/needrestart/dpkg-status` ran during a chrootless target transaction;
- the logger created root-owned host file `/run/needrestart/unpacked`;
- disabling the host needrestart dpkg fragment removed both execution and host mutation;
- later testing with a temporary user `~/.dpkg.cfg` showed that `--status-logger=` and `--status-logger=true` did not remove the configured logger.

The new probe separates user and system configuration and confirms that the environment scrub only closes the user-config path. The system-config path remains active.

## Mechanism

Current dpkg accepts ordinary command-line options from three configuration locations:

1. `/etc/dpkg/dpkg.cfg.d/[0-9A-Za-z_-]*`;
2. `/etc/dpkg/dpkg.cfg`;
3. `~/.dpkg.cfg` when `HOME` is set.

The command-bearing options relevant here are:

- `pre-invoke`;
- `post-invoke`;
- `status-logger`.

They are repeatable. Later command-line values add commands rather than deleting commands loaded from configuration. Both invoke hooks and status loggers are enabled in the same `--force-not-root` transaction form used by chrootless mode.

Other configuration options alter target results without running commands. Path include/exclude rules are ordered filters. The retained probe shows that one final `path-include *` restores the controlled package paths, but that only handles the path-filter class. A configured `no-act`, selection option, force policy, trigger policy, dependency override, root/admin directory, or another operation option may still change the transaction.

No current documented dpkg option or environment variable selects an empty configuration set before normal option parsing. Appending options after configuration loading therefore cannot provide general isolation.

## Security and correctness boundary

This is confirmed host command execution and target-policy inheritance, but the claim must remain bounded.

- Chrootless maintainer scripts already execute as host processes.
- An unprivileged run executes host-configured commands with the invoking user's authority.
- A root run after bypassing mmdebstrap's root safety check executes them with root authority; LF-02 demonstrated a real root-owned host mutation.
- The package itself does not need to supply the host configuration for the effect to occur.
- This is not, by itself, a new privilege escalation from an untrusted package: chrootless package scripts already possess the caller's host authority.
- The concrete defects are unowned host integrations, silent target divergence, surprising command execution, and inability to reset additive hooks from the caller.

## Why this should not be folded into the four-patch submission

The existing series has one narrow owner: construction of the maintainer-script launch environment and executable lookup. Host dpkg configuration is parsed by dpkg before those package scripts run and has a different compatibility problem.

Adding an incomplete hook blacklist to the environment PR would create a broad claim that the patch cannot satisfy. The current unit should remain one reviewable four-commit correction. Dpkg configuration isolation should be a separate held correction or a coordinated dpkg/mmdebstrap change.

## Candidate correction directions

### 1. Dpkg feature: explicit configuration selection

The clean interface is a dpkg option available before ordinary configuration parsing, such as an exact `--no-config` or `--config-file=/dev/null` contract. mmdebstrap could require or feature-detect that interface for chrootless mode.

Advantages:

- complete rather than option-specific;
- easy to reason about;
- preserves host dpkg binary and libraries;
- supports both direct and apt-managed dpkg calls.

Cost:

- requires dpkg work before mmdebstrap can fully use it;
- needs a compatibility path for older dpkg versions.

### 2. Fail-closed mmdebstrap preflight

Parse the exact system dpkg configuration files and reject chrootless execution when options outside a small accepted set are active. Report file paths and option names, never command values. Permit one explicit risk override.

Potentially neutralizable classes:

- force a final target-local `log`;
- force a final `path-include *` to cancel inherited path filters.

Must reject at minimum:

- `pre-invoke`;
- `post-invoke`;
- `status-logger`;
- `no-act` and any other option with no proven inverse;
- unknown options until classified.

Risks:

- reimplementing dpkg configuration parsing and option semantics;
- rejecting legitimate local policy;
- future dpkg options becoming unsafe unless unknown options fail closed;
- still no true guarantee if configuration files change between inspection and dpkg opening them.

### 3. Private mount/configuration namespace

Run dpkg in a namespace where `/etc/dpkg/dpkg.cfg` and `/etc/dpkg/dpkg.cfg.d` expose a controlled empty configuration while the host binary and libraries remain available.

Risks:

- ordinary unprivileged chrootless operation does not universally have mount-namespace authority;
- user-namespace and helper requirements change the mode contract;
- setup and teardown become another privileged lifecycle;
- this begins to overlap with fakechroot, unshare, or bubblewrap-style execution rather than a small correction.

## Next test matrix

1. Adapt the retained probe to the exact four-patch mirror candidate after the series is applied.
2. Execute both direct Essential installation and apt-managed installation with a controlled system fragment containing each command hook independently.
3. Confirm that clearing `HOME` removes user configuration on both paths.
4. Confirm final `path-include *` and target-local `log` behavior on direct and apt-managed paths.
5. Add separate controls for `no-act`, trigger policy, force policy, root/admin directory options, and unknown options.
6. Inventory default dpkg fragments on current Debian, Ubuntu, and container images before selecting a fail-closed allowlist.
7. Recheck current dpkg development documentation for an official configuration-disable interface before designing a local parser.
8. Keep APT logind inhibition separate: it is an APT policy path with existing exact options, not a dpkg configuration-file correction.

## Disposition

- Four-patch environment/TMPDIR/PATH/env-wrapper candidate: continue as unit 06.
- Host dpkg configuration isolation: `HOLD` pending choice between a dpkg interface and a bounded fail-closed mmdebstrap preflight.
- APT host shutdown/sleep inhibition: separate policy decision.
- External disclosure: none authorized or made.
