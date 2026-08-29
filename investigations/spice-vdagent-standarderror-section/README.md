# spice-vdagent places `StandardError` in the wrong unit section

## In simple words

Ubuntu 26.04's `spice-vdagent 0.23.0-1` installs a user service with
`StandardError=null` below `[Install]`. `StandardError` is a service-execution
setting, so systemd ignores it and logs a warning every time it reloads the
unit. Debian already fixed the packaging in `0.23.0-2`.

On physical `big-red`, the SPICE guest socket is absent and the conditional
service never starts. The local consequence is verifier/journal noise, not a
ChatGPT Remote, GNOME Remote Desktop, or SSH failure. Carrying a full local
unit override would hide the warning but also shadow the eventual package fix,
so no host change is warranted.

## Current state

- State: `COMPLETE`
- Exact working head: installed Ubuntu package `spice-vdagent 0.23.0-1`
- Latest authoritative gate or artifact: installed-unit and corrected-unit
  `systemd-analyze --user verify` comparison
- First incomplete step: none for the bounded host diagnosis
- Cleanup state: no service, package, unit, process, or socket changed; the
  corrected test fixture was removed after verification
- Next safe action: accept the harmless warning until Ubuntu ships the Debian
  fix; recheck the packaged unit after an ordinary update
- External-contact state: no Ubuntu, Debian, or SPICE contact authorized or
  made

## Intent and precedent

The adjacent comment says `spice-vdagent` logs through syslog and stderr and
that stderr should be disconnected to avoid duplicates. Debian's current
`0.23.0-3` source keeps that comment and `StandardError=null` in `[Service]`,
before `[Install]`:

- [Debian source unit](https://sources.debian.org/src/spice-vdagent/0.23.0-3/data/spice-vdagent.service/)
- [Debian bug 1132849](https://bugs.debian.org/1132849)

The Debian changelog for `0.23.0-2` explicitly records moving the directive
out of `[Install]` and closing that bug. This is a known packaging mistake, not
a new systemd or SPICE upstream behavior.

## Source

- Project: Debian/Ubuntu packaging for `spice-vdagent`
- Requested revision or package version: Ubuntu `0.23.0-1`
- Resolved package: `spice-vdagent 0.23.0-1` for amd64
- Candidate source commit: none
- Local source path: `/usr/lib/systemd/user/spice-vdagent.service`
- Import metadata: none

## Environment

- Distribution and release: Ubuntu 26.04.1 LTS
- Kernel and architecture: Linux `7.0.0-30-generic`, x86-64
- Shell: Bash for the probe; systemd user manager for parsing
- Privileges: unprivileged reads and verification only
- Host context: physical REDMI Book Pro 16 2025, not a SPICE guest
- Relevant tool versions: systemd from Ubuntu 26.04.1; `spice-vdagent 0.23.0-1`

## Baseline behavior

The installed file has `[Install]` at line 18 and `StandardError=null` at line
23. Verification emits:

```text
/usr/lib/systemd/user/spice-vdagent.service:23: Unknown key 'StandardError' in section [Install], ignoring.
```

The user journal contained fourteen copies during the current session. The
unit is enabled but inactive because
`/run/spice-vdagentd/spice-vdagent-sock` does not exist; its condition failure
is correct on this physical host.

## Reproduction

```sh
dpkg-query -W spice-vdagent
nl -ba /usr/lib/systemd/user/spice-vdagent.service
systemd-analyze --user verify /usr/lib/systemd/user/spice-vdagent.service
test -e /run/spice-vdagentd/spice-vdagent-sock
```

For the candidate control, move only `StandardError=null` immediately after
`ExecStart` in a disposable copy and verify that copy with the same command.

## Results

- The installed unit deterministically produces the unknown-key warning.
- The corrected disposable copy produces no warning.
- The service condition is unmet and no SPICE agent process is running.
- Debian `0.23.0-2` already owns the same correction; current Debian
  `0.23.0-3` retains it.

## Interpretation

Systemd is behaving as documented by ignoring a service-execution directive in
the install metadata section. The package's intended stderr suppression is not
applied if the agent runs, but that path is dormant on `big-red`. The correct
repair owner is the distribution package update. A machine-local copied unit
would have a larger maintenance cost than the current warning.

## Evidence boundary

The corrected unit was parser-verified but not started because the required
SPICE socket is intentionally absent. This does not test a real SPICE guest,
stderr duplication during an active agent session, or Ubuntu's eventual update
version. It does establish the parser warning, the exact section error, the
known fixed Debian version, and the lack of current host impact.

## Next step

Retain this as an explained downstream-version-lag result. After Ubuntu updates
`spice-vdagent`, verify that `StandardError=null` appears under `[Service]` and
that `systemd-analyze --user verify` is quiet. Do not create a persistent local
override merely to silence the warning.

## Authority

Internal research and sanitized evidence retention are authorized. No upstream
or distribution issue, comment, merge request, or patch submission has been
authorized or created.
