# LF-02 expanded host-integration findings

## In simple words

Three sharper host boundaries reproduced cleanly.

1. A root chrootless transaction executed Ubuntu's host `needrestart` dpkg status logger and created `/run/needrestart/unpacked` on the host.
2. APT connected to host systemd-logind, requested a blocking shutdown inhibitor, and received a real inhibitor file descriptor. Setting `DPkg::Inhibit-Shutdown "false"` and `DPkg::Inhibit-Sleep "false"` removed that system-bus interaction while target package state stayed identical.
3. Maintainer scripts inherited fake cloud credentials and host session variables from the caller. An inherited fake `SSH_AUTH_SOCK` let the package script connect to a host Unix socket and send a canary message. A blank-environment control removed the credentials and socket access.

These are stronger than the first unprivileged observation because they distinguish attempted host activity from successful host mutation, provide controls that remove each effect independently, and demonstrate a direct caller-credential/IPC path.

## Source and execution boundary

- Imported source: `upstream/mmdebstrap/mmdebstrap`
- Requested revision: `debian/1.5.7-3`
- Resolved upstream commit: `6fde999741f4fe1e7bf38079acf29432ef87a35e`
- Follow-up branch: `investigation/lf-02-privileged-host-integrations`
- Draft PR: `#22`
- GitHub Actions run: `30530666222`
- Job: `90831976076`
- Artifact: `8754537765`
- Artifact digest: `sha256:5c7d978934983858438a08f737c2596b892ec8151f676175ff0edae586f43c5b`
- Runner: GitHub-hosted Ubuntu 24.04
- No upstream contact

## Privileged host-integration matrix

All three builds used the same local dependency-free LF-02 package, fresh targets, `--mode=chrootless`, `--variant=custom`, directory output, local package input, and skipped repository update.

| Case | APT inhibitors | Host needrestart dpkg config | Exit | System bus | needrestart | Host marker |
|---|---|---|---:|---|---|---|
| `default-root` | enabled | enabled | 0 | connected; inhibitor FD received | executed | created |
| `no-inhibit-root` | disabled | enabled | 0 | absent | executed | created |
| `isolated-root` | disabled | temporarily disabled | 0 | absent | absent | absent |

Normalized maintainer-script observations and `update-alternatives` state were identical across all three targets.

### Successful host mutation

Before `default-root`, `/run/needrestart/unpacked` was absent. The trace then recorded:

```text
execve("/usr/lib/needrestart/dpkg-status", ... /* 127 vars */) = 0
execve("/usr/bin/touch", ["touch", "/run/needrestart/unpacked"], ... /* 127 vars */) = 0
openat(..., "/run/needrestart/unpacked", O_WRONLY|O_CREAT|..., 0666) = 1</run/needrestart/unpacked>
utimensat(0</run/needrestart/unpacked>, NULL, NULL, 0) = 0
```

After the transaction the marker existed as an empty root-owned mode-0644 host file. The probe restored its original absent state through the exit trap.

Disabling APT's shutdown/sleep inhibitors left this mutation unchanged. Temporarily moving aside `/etc/dpkg/dpkg.cfg.d/needrestart` removed the logger execution and host marker creation.

### Host logind inhibitor

The default root case connected successfully to `/run/dbus/system_bus_socket` and sent:

```text
org.freedesktop.login1.Manager.Inhibit(
  "shutdown",
  "APT",
  "APT is installing or removing packages",
  "block"
)
```

The reply carried `SCM_RIGHTS` with `/run/systemd/inhibit/3.ref`, proving that APT acquired a live host shutdown-inhibitor descriptor.

Passing these target APT options removed the system-bus connection and logind call:

```text
DPkg::Inhibit-Shutdown "false";
DPkg::Inhibit-Sleep "false";
```

Target package state remained identical.

## Environment and host-agent canary

The inherited case launched the same chrootless package operation with fake values only:

```text
LF_SECRET_CANARY=lf-secret-canary-7f46
AWS_SECRET_ACCESS_KEY=fake-aws-secret-3a91
GITHUB_TOKEN=fake-github-token-91c2
SSH_AUTH_SOCK=<fake host Unix socket>
DBUS_SESSION_BUS_ADDRESS=<fake host session-bus path>
```

The maintainer script observed 133 environment entries, recorded every fake credential and path, connected to the fake host `SSH_AUTH_SOCK`, and sent:

```text
lf-fieldwork-package-script
```

The blank-environment control exposed 19 entries, reported the credential and session variables as unset, and skipped the socket connection.

No real secret, SSH agent, cloud credential, or session bus was used.

## Ranking

### 1. Caller credential and agent inheritance

This is the strongest security follow-up. Chrootless maintainer scripts can receive caller-provided credential variables and use inherited host IPC endpoints. The next probe should inventory mmdebstrap's required environment and test a minimal allowlist or explicit denylist for secret- and session-bearing variables.

### 2. Host dpkg status-loggers under root

This is a concrete successful host mutation caused by host dpkg configuration during a target-root transaction. A follow-up should test a command-line status-logger override or a dedicated chrootless suppression option, then verify compatibility across Debian and Ubuntu dpkg configurations.

### 3. APT's host shutdown inhibitor

The behavior is intentional APT policy, yet it changes host service state during target construction. The existing APT options provide a precise control. A follow-up should decide whether chrootless mode should disable these inhibitors by default or expose an explicit mmdebstrap option.

### 4. Wider host configuration execution

The needrestart result validates the general host-dpkg-config concern. Other host `status-logger`, path-filtering, and command-bearing dpkg settings deserve an inventory, with priority given to settings that execute commands or alter target contents silently.

## Evidence limits

- The privileged runner was disposable and all changed host sentinels/configuration were restored.
- The environment test used fake credentials and a purpose-built Unix socket. It demonstrates reachability and data transfer, not a real SSH-agent protocol operation.
- Chrootless maintainer scripts already execute host programs and can issue host syscalls. The environment result identifies a convenient credential and IPC discovery path; it does not claim that environment inheritance is unique to mmdebstrap.
- The package fixture is synthetic and cooperative. Real packages with service, account, boot, and cache hooks remain useful next targets.
- Raw traces expire with the workflow artifact; compact summaries and key evidence are retained in this branch.

## Decision

**Promising follow-up areas confirmed.** Retain PR #22 as an investigation record. The environment/agent path and privileged host dpkg logger deserve deeper candidate-mitigation probes before any upstream action.
