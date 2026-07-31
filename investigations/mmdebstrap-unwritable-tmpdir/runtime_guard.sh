#!/usr/bin/env bash

validate_disposable_runtime() {
  local repository=$1
  local home_input=$2
  local parent_input=$3
  local leaf=$4
  local repository_root home_root runtime_parent runtime_root

  case "$leaf" in
    ''|.|..|*/*)
      echo "refusing unsafe runtime leaf: $leaf" >&2
      return 2
      ;;
  esac

  repository_root="$(realpath -m "$repository")"
  home_root="$(realpath -m "$home_input")"
  runtime_parent="$(realpath -m "$parent_input")"

  case "$repository_root" in
    /)
      echo "refusing repository root as cleanup boundary" >&2
      return 2
      ;;
  esac
  case "$home_root" in
    /)
      echo "refusing home root as cleanup boundary" >&2
      return 2
      ;;
  esac

  case "$runtime_parent" in
    /tmp|/tmp/*|/var/tmp|/var/tmp/*|/home/runner/work/_temp|/home/runner/work/_temp/*)
      ;;
    *)
      echo "refusing unsafe runtime parent: $runtime_parent" >&2
      return 2
      ;;
  esac

  runtime_root="$(realpath -m "$runtime_parent/$leaf")"
  case "$runtime_root" in
    "$runtime_parent"/*)
      ;;
    *)
      echo "refusing runtime outside selected parent: $runtime_root" >&2
      return 2
      ;;
  esac

  case "$runtime_root" in
    "$repository_root"|"$repository_root"/*)
      echo "refusing runtime inside repository: $runtime_root" >&2
      return 2
      ;;
  esac
  case "$repository_root" in
    "$runtime_root"|"$runtime_root"/*)
      echo "refusing runtime containing repository: $runtime_root" >&2
      return 2
      ;;
  esac

  case "$runtime_parent" in
    /home/runner/work/_temp|/home/runner/work/_temp/*)
      case "$home_root" in
        "$runtime_root"|"$runtime_root"/*)
          echo "refusing hosted runtime containing home: $runtime_root" >&2
          return 2
          ;;
      esac
      ;;
    *)
      case "$runtime_root" in
        "$home_root"|"$home_root"/*)
          echo "refusing runtime inside home: $runtime_root" >&2
          return 2
          ;;
      esac
      case "$home_root" in
        "$runtime_root"|"$runtime_root"/*)
          echo "refusing runtime containing home: $runtime_root" >&2
          return 2
          ;;
      esac
      ;;
  esac

  printf '%s\n' "$runtime_root"
}
