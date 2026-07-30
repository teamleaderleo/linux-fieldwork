{ nixpkgsRev, mode }:

assert builtins.elem mode [
  "baseline"
  "unset-goflags"
  "filter-goflags"
  "add-fixture"
  "add-fixture-filter-goflags"
];

let
  nixpkgsPath = builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/${nixpkgsRev}.tar.gz";
  };
  pkgs = import nixpkgsPath { };
  lib = pkgs.lib;
  addFixture = builtins.elem mode [
    "add-fixture"
    "add-fixture-filter-goflags"
  ];
  unsetGoFlags = mode == "unset-goflags";
  filterGoFlags = builtins.elem mode [
    "filter-goflags"
    "add-fixture-filter-goflags"
  ];
in
pkgs.gomarkdoc.overrideAttrs (old: {
  doCheck = true;

  postPatch = (old.postPatch or "") + lib.optionalString addFixture ''
    # gomarkdoc v1.1.0 references this explicit empty configuration from
    # command_test.go, but the tagged source archive does not contain it.
    : > .gomarkdoc-empty.yml
  '';

  preCheck = (old.preCheck or "") + ''
    printf 'FIELDWORK mode=%s initial_GOFLAGS=%q pwd=%q\n' \
      ${lib.escapeShellArg mode} "''${GOFLAGS-}" "$PWD"
  '' + lib.optionalString unsetGoFlags ''
    unset GOFLAGS
    printf 'FIELDWORK mode=%s effective_GOFLAGS=<unset>\n' \
      ${lib.escapeShellArg mode}
  '' + lib.optionalString filterGoFlags ''
    # gomarkdoc intentionally reads GOFLAGS only to recover Go build tags.
    # Keep -tags spellings while removing Nixpkgs' builder-only module and
    # reproducibility flags from the in-process command parser.
    declare -a fieldwork_goflags=()
    fieldwork_expect_tags=0
    for fieldwork_token in ''${GOFLAGS-}; do
      if [[ "$fieldwork_expect_tags" == 1 ]]; then
        fieldwork_goflags+=("$fieldwork_token")
        fieldwork_expect_tags=0
        continue
      fi
      case "$fieldwork_token" in
        -tags)
          fieldwork_goflags+=("$fieldwork_token")
          fieldwork_expect_tags=1
          ;;
        -tags=*)
          fieldwork_goflags+=("$fieldwork_token")
          ;;
      esac
    done
    if (( ''${#fieldwork_goflags[@]} )); then
      printf -v GOFLAGS '%s ' "''${fieldwork_goflags[@]}"
      export GOFLAGS="''${GOFLAGS% }"
    else
      unset GOFLAGS
    fi
    printf 'FIELDWORK mode=%s effective_GOFLAGS=%q\n' \
      ${lib.escapeShellArg mode} "''${GOFLAGS-}"
  '';
})
