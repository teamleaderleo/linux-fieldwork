#!/usr/bin/env bash
# Prove whether util-linux fsck -l and udev's whole-device flock share a lock domain.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
run_id=${RUN_ID:-"local-$(date -u +%Y%m%dT%H%M%SZ)"}
run_dir=${RUN_DIR:-"$repo_root/investigations/fsck-udev-lock-identity/runs/$run_id"}
mkdir -p "$run_dir"

finish_early() {
  local status=$1
  shift
  printf '%s\n' "$*" >&2
  printf '%s\n' "$status" >"$run_dir/exit-status"
  printf '%s\n' "$*" >"$run_dir/preflight-error.txt"
  exit "$status"
}

if [[ $(id -u) -ne 0 ]]; then
  finish_early 77 "probe requires root in a disposable privileged container"
fi
for command in fsck flock losetup lslocks mount mountpoint python3 stat truncate umount; do
  command -v "$command" >/dev/null 2>&1 || finish_early 77 "$command is unavailable"
done
[[ -e /dev/loop-control ]] || finish_early 77 "/dev/loop-control is unavailable"

work_root=$(mktemp -d "${TMPDIR:-/tmp}/lf-fsck-lock.XXXXXXXX")
image="$work_root/disk.img"
fake_path="$work_root/fake-checkers"
checker_ready="$work_root/checker-ready"
checker_release="$work_root/checker-release"
exclusive_ready="$work_root/exclusive-ready"
exclusive_release="$work_root/exclusive-release"
rotational_override="$work_root/rotational-override"
loopdev=
fsck_pid=
exclusive_pid=
lockpath=
rotational_path=
rotational_override_mounted=0

cleanup() {
  set +e
  [[ -n ${fsck_pid:-} ]] && kill "$fsck_pid" 2>/dev/null
  [[ -n ${exclusive_pid:-} ]] && kill "$exclusive_pid" 2>/dev/null
  [[ -n ${fsck_pid:-} ]] && wait "$fsck_pid" 2>/dev/null
  [[ -n ${exclusive_pid:-} ]] && wait "$exclusive_pid" 2>/dev/null
  if [[ $rotational_override_mounted -eq 1 && -n ${rotational_path:-} ]]; then
    umount "$rotational_path" 2>/dev/null
  fi
  if [[ -n ${loopdev:-} ]]; then
    losetup -d "$loopdev" 2>/dev/null
  fi
  if [[ -n ${lockpath:-} && $lockpath == /run/fsck/loop*.lock ]]; then
    rm -f -- "$lockpath"
  fi
  rm -rf -- "$work_root"
}
trap cleanup EXIT INT TERM

truncate -s 32M "$image"
loopdev=$(losetup --find --show "$image")
loopname=${loopdev##*/}
lockpath="/run/fsck/$loopname.lock"
rotational_path=$(readlink -f "/sys/class/block/$loopname/queue/rotational")
[[ -f $rotational_path ]] || finish_early 77 "rotational attribute is unavailable for $loopdev"
rotational_original=$(cat "$rotational_path")
printf '%s\n' "$rotational_original" >"$run_dir/rotational-original.txt"

# fsck -l deliberately skips non-rotating devices. Override only this container's
# mount-namespace view of the loop queue attribute so the current fsck lock path
# executes without modifying the host kernel attribute.
printf '1\n' >"$rotational_override"
if ! mount --bind "$rotational_override" "$rotational_path" \
    >"$run_dir/rotational-bind.stdout" 2>"$run_dir/rotational-bind.stderr"; then
  finish_early 77 "unable to bind a private rotational=1 fixture over $rotational_path"
fi
rotational_override_mounted=1
printf '%s\n' "$(cat "$rotational_path")" >"$run_dir/rotational-effective.txt"
[[ $(cat "$rotational_path") == 1 ]] || finish_early 2 "rotational override did not become effective"
findmnt -T "$rotational_path" >"$run_dir/rotational-mount.txt" || true

rm -f -- "$lockpath"
mkdir -p "$fake_path"
cat >"$fake_path/fsck.ext4" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${LOCK_PROBE_READY:?}"
: "${LOCK_PROBE_RELEASE:?}"
printf '%s\n' "$$" >"$LOCK_PROBE_READY"
printf '%s\n' "$0" >"$LOCK_PROBE_READY.executable"
printf '%q ' "$@" >"$LOCK_PROBE_READY.argv"
printf '\n' >>"$LOCK_PROBE_READY.argv"
while [[ ! -e $LOCK_PROBE_RELEASE ]]; do
  sleep 0.05
done
exit 0
EOF
chmod 0755 "$fake_path/fsck.ext4"

{
  printf '# fsck/udev lock identity probe\n\n'
  printf -- '- Started: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Run ID: `%s`\n' "$run_id"
  printf -- '- Loop device: `%s`\n' "$loopdev"
  printf -- '- Rotational attribute: `%s`\n' "$rotational_path"
  printf -- '- Original rotational value: `%s`\n' "$rotational_original"
  printf -- '- Effective private-fixture value: `%s`\n' "$(cat "$rotational_path")"
  printf '\n## Versions\n\n```text\n'
  uname -a
  fsck --version 2>&1 | head -1
  flock --version 2>&1 | head -1
  losetup --version 2>&1 | head -1
  printf '```\n'
} >"$run_dir/context.md"

set +e
PATH="$fake_path:/usr/sbin:/usr/bin:/sbin:/bin" \
LOCK_PROBE_READY="$checker_ready" \
LOCK_PROBE_RELEASE="$checker_release" \
  fsck -l -t ext4 "$loopdev" \
  >"$run_dir/fsck.stdout" 2>"$run_dir/fsck.stderr" &
fsck_pid=$!
set -e
printf '%s\n' "$fsck_pid" >"$run_dir/fsck-front-end.pid"

for _ in $(seq 1 200); do
  [[ -s $checker_ready && -e $lockpath ]] && break
  if ! kill -0 "$fsck_pid" 2>/dev/null; then
    wait "$fsck_pid" || true
    finish_early 2 "fsck front-end exited before holding the fake checker and private lock"
  fi
  sleep 0.05
done
[[ -s $checker_ready ]] || finish_early 2 "fake checker did not start"
[[ -e $lockpath ]] || finish_early 2 "fsck -l did not create $lockpath despite rotational=1 fixture"
cp "$checker_ready.executable" "$run_dir/fake-checker.executable"
cp "$checker_ready.argv" "$run_dir/fake-checker.argv"

checker_pid=$(cat "$checker_ready")
printf '%s\n' "$checker_pid" >"$run_dir/fake-checker.pid"
stat -Lc 'path=%n inode=%i mode=%f dev=%D rdev=%t:%T size=%s' \
  "$lockpath" "$loopdev" >"$run_dir/lock-objects.txt"
lslocks --json >"$run_dir/lslocks-during-fsck.json" || true
cat /proc/locks >"$run_dir/proc-locks-during-fsck.txt"

# Positive control: fsck really holds the private /run/fsck lock exclusively.
set +e
flock -sn "$lockpath" true
private_shared_status=$?
set -e
printf '%s\n' "$private_shared_status" >"$run_dir/private-lock-shared-probe.status"

# Distinguishing probe: udev's shared whole-device lock can coexist if lock domains differ.
set +e
flock -sn "$loopdev" true
whole_shared_during_fsck_status=$?
set -e
printf '%s\n' "$whole_shared_during_fsck_status" \
  >"$run_dir/whole-device-shared-during-fsck.status"

# Release fsck and require ordinary completion.
touch "$checker_release"
set +e
wait "$fsck_pid"
fsck_status=$?
set -e
fsck_pid=
printf '%s\n' "$fsck_status" >"$run_dir/fsck-exit-status"

# Negative control: the documented whole-device exclusive lock blocks a udev-equivalent shared probe.
(
  exec 9<>"$loopdev"
  flock -x 9
  touch "$exclusive_ready"
  while [[ ! -e $exclusive_release ]]; do
    sleep 0.05
  done
) >"$run_dir/exclusive-holder.stdout" 2>"$run_dir/exclusive-holder.stderr" &
exclusive_pid=$!
for _ in $(seq 1 200); do
  [[ -e $exclusive_ready ]] && break
  kill -0 "$exclusive_pid" 2>/dev/null || finish_early 2 "exclusive whole-device holder exited early"
  sleep 0.05
done
[[ -e $exclusive_ready ]] || finish_early 2 "exclusive whole-device holder did not become ready"

set +e
flock -sn "$loopdev" true
whole_shared_under_exclusive_status=$?
set -e
printf '%s\n' "$whole_shared_under_exclusive_status" \
  >"$run_dir/whole-device-shared-under-exclusive.status"
lslocks --json >"$run_dir/lslocks-during-exclusive.json" || true
cat /proc/locks >"$run_dir/proc-locks-during-exclusive.txt"

touch "$exclusive_release"
wait "$exclusive_pid"
exclusive_pid=

classification=pass
final_status=0
if [[ $private_shared_status -eq 0 ]]; then
  classification=failed-positive-control-private-lock-not-held
  final_status=2
elif [[ $whole_shared_during_fsck_status -ne 0 ]]; then
  classification=lock-domains-not-independent
  final_status=2
elif [[ $whole_shared_under_exclusive_status -eq 0 ]]; then
  classification=failed-negative-control-whole-device-lock-did-not-conflict
  final_status=2
elif [[ $fsck_status -ne 0 ]]; then
  classification=fsck-carrier-failure
  final_status=$fsck_status
fi

{
  printf '# Result\n\n'
  printf -- '- Finished: `%s`\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf -- '- Classification: `%s`\n' "$classification"
  printf -- '- Private lock shared probe while fsck active: `%s` (expected nonzero)\n' "$private_shared_status"
  printf -- '- Whole-device shared probe while fsck active: `%s` (expected zero)\n' "$whole_shared_during_fsck_status"
  printf -- '- Whole-device shared probe under whole-device exclusive lock: `%s` (expected nonzero)\n' "$whole_shared_under_exclusive_status"
  printf -- '- fsck carrier exit: `%s`\n' "$fsck_status"
  printf -- '- Final exit: `%s`\n' "$final_status"
  printf '\n## Interpretation\n\n'
  if [[ $classification == pass ]]; then
    printf 'Current `fsck -l` coordination and the udev whole-device flock occupy independent lock objects. The documented whole-device exclusive/shared protocol conflicts as expected. This proves the lock-domain gap, not the ext4 UUID race.\n'
  else
    printf 'The expected lock-domain contract was not observed; inspect raw receipts before making a product claim.\n'
  fi
} >"$run_dir/RESULT.md"

printf '%s\n' "$final_status" >"$run_dir/exit-status"
exit "$final_status"
