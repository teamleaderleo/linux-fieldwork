{ firmwareRev, qemuRev }:

let
  sourceFor = rev: builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/${rev}.tar.gz";
  };
  hostPkgs = import (sourceFor qemuRev) { system = "x86_64-linux"; };
  firmwarePkgs = import (sourceFor firmwareRev) { system = "aarch64-linux"; };
  firmware = firmwarePkgs.OVMFFull.fd;
  systemdBoot = firmwarePkgs.systemd;
in
hostPkgs.writeShellApplication {
  name = "aavmf-gic-case";
  runtimeInputs = [
    hostPkgs.coreutils
    hostPkgs.findutils
    hostPkgs.gnugrep
    hostPkgs.util-linux
  ];
  text = ''
    set -euo pipefail

    mode="''${1:?GIC mode is required}"
    case_dir="''${2:?case directory is required}"
    timeout_seconds="''${AAVMF_CASE_TIMEOUT:-60}"

    case "$mode" in
      default|2|3|max) ;;
      *)
        echo "unsupported GIC mode: $mode" >&2
        exit 2
        ;;
    esac

    if [[ -e "$case_dir" ]]; then
      echo "refusing to reuse case directory: $case_dir" >&2
      exit 2
    fi
    mkdir -p "$case_dir"

    firmware_code="${firmware}/FV/AAVMF_CODE.fd"
    firmware_vars="${firmware}/FV/AAVMF_VARS.fd"
    systemd_boot="${systemdBoot}/lib/systemd/boot/efi/systemd-bootaa64.efi"
    qemu="${hostPkgs.qemu}/bin/qemu-system-aarch64"

    for required in "$firmware_code" "$firmware_vars" "$systemd_boot" "$qemu"; do
      if [[ ! -f "$required" || ! -r "$required" ]]; then
        echo "missing required exact artifact: $required" >&2
        exit 2
      fi
    done
    if [[ ! -x "$qemu" ]]; then
      echo "QEMU is not executable: $qemu" >&2
      exit 2
    fi

    work="$(mktemp -d -- "$case_dir/work.XXXXXXXX")"
    efi_dir="$work/efi"
    vars_file="$work/AAVMF_VARS.fd"
    log_file="$case_dir/qemu.log"
    command_file="$case_dir/command.txt"
    outcome_file="$case_dir/outcome.txt"
    qemu_pid=""

    cleanup() {
      local status=$?
      trap - EXIT INT TERM
      if [[ -n "$qemu_pid" ]] && kill -0 "$qemu_pid" 2>/dev/null; then
        kill -TERM -- "-$qemu_pid" 2>/dev/null || true
        for _ in $(seq 1 20); do
          if ! kill -0 "$qemu_pid" 2>/dev/null; then
            break
          fi
          sleep 0.05
        done
        if kill -0 "$qemu_pid" 2>/dev/null; then
          kill -KILL -- "-$qemu_pid" 2>/dev/null || true
        fi
        wait "$qemu_pid" 2>/dev/null || true
      fi
      if [[ -d "$work" && ! -L "$work" && "$work" == "$case_dir"/work.* ]]; then
        rm -rf -- "$work"
      fi
      exit "$status"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    mkdir -p "$efi_dir/EFI/BOOT" "$efi_dir/loader/entries"
    cp -- "$systemd_boot" "$efi_dir/EFI/BOOT/BOOTAA64.EFI"
    printf '%s\n' \
      'timeout 5' \
      'editor no' \
      'console-mode keep' \
      >"$efi_dir/loader/loader.conf"
    cp -- "$firmware_vars" "$vars_file"
    chmod u+w "$vars_file"
    : >"$log_file"

    qemu_command=(
      "$qemu"
      -accel tcg,thread=multi
      -cpu max
      -smp 2
      -m 1024
      -nographic
      -serial stdio
      -monitor none
      -no-reboot
      -drive "if=pflash,format=raw,unit=0,readonly=on,file=$firmware_code"
      -drive "if=pflash,format=raw,unit=1,file=$vars_file"
      -drive "if=virtio,format=raw,file=fat:rw:$efi_dir"
    )
    if [[ "$mode" == default ]]; then
      qemu_command+=( -machine virt )
    else
      qemu_command+=( -machine "virt,gic-version=$mode" )
    fi

    printf '%q ' "''${qemu_command[@]}" >"$command_file"
    printf '\n' >>"$command_file"
    "$qemu" --version >"$case_dir/qemu-version.txt"
    printf '%s\n' "$firmware_code" >"$case_dir/firmware-code.txt"
    printf '%s\n' "$firmware_vars" >"$case_dir/firmware-vars.txt"
    printf '%s\n' "$systemd_boot" >"$case_dir/systemd-boot.txt"

    setsid "''${qemu_command[@]}" >"$log_file" 2>&1 &
    qemu_pid=$!
    deadline=$((SECONDS + timeout_seconds))

    while true; do
      if grep -F 'Boot in 5 s.' "$log_file" >/dev/null 2>&1 ||
         grep -F 'systemd-boot' "$log_file" >/dev/null 2>&1; then
        printf 'pass\n' >"$outcome_file"
        exit 0
      fi
      if ! kill -0 "$qemu_pid" 2>/dev/null; then
        set +e
        wait "$qemu_pid"
        qemu_status=$?
        set -e
        qemu_pid=""
        printf 'early-exit:%s\n' "$qemu_status" >"$outcome_file"
        exit 1
      fi
      if (( SECONDS >= deadline )); then
        printf 'timeout\n' >"$outcome_file"
        exit 1
      fi
      sleep 1
    done
  '';
}
