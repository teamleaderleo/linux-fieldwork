#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)
BASELINE=$REPO_ROOT/upstream/mmdebstrap/gpgvnoexpkeysig
PATCH=$REPO_ROOT/investigations/mmdebstrap-gpgvnoexpkeysig-canonical/0001-canonical-lifecycle.patch
RELEASE=$SCRIPT_DIR/../fixtures/Release
EXPECTED_BASELINE_BLOB=83370755454a1322bf6862751aab7381d175aa8b
EXPECTED_CANDIDATE_BLOB=de7e0ae24218632fe2e32a1130f5c2a39f8c4aed

for command_name in apt-get gpg gpgv git id md5sum patch sha256sum stat; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: $command_name" >&2
    exit 77
  fi
done

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/unit03-real-gpg.XXXXXXXXXX")
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT HUP INT TERM

SOURCE_TREE=$WORKDIR/source
mkdir -p "$SOURCE_TREE/upstream/mmdebstrap"
cp "$BASELINE" "$SOURCE_TREE/upstream/mmdebstrap/gpgvnoexpkeysig"
patch -s -d "$SOURCE_TREE" -p1 <"$PATCH"
CANDIDATE=$SOURCE_TREE/upstream/mmdebstrap/gpgvnoexpkeysig
chmod +x "$CANDIDATE"

BASELINE_BLOB=$(git hash-object "$BASELINE")
CANDIDATE_BLOB=$(git hash-object "$CANDIDATE")
[ "$BASELINE_BLOB" = "$EXPECTED_BASELINE_BLOB" ]
[ "$CANDIDATE_BLOB" = "$EXPECTED_CANDIDATE_BLOB" ]
/bin/sh -n "$BASELINE"
/bin/sh -n "$CANDIDATE"

GNUPGHOME=$WORKDIR/gnupg
export GNUPGHOME
mkdir -m 700 "$GNUPGHOME"
cp "$RELEASE" "$WORKDIR/Release"
mkdir "$WORKDIR/candidate-tmp"

GPG_VERSION=$(gpg --version | sed -n '1p')
GPGV_VERSION=$(gpgv --version | sed -n '1p')

gpg --batch --pinentry-mode loopback --passphrase '' \
  --faked-system-time 20000101T000000 \
  --quick-generate-key \
  'Linux Fieldwork Unit 03 <unit03@example.invalid>' rsa2048 sign 1d \
  >/dev/null 2>"$WORKDIR/keygen.stderr"

FINGERPRINT=$(gpg --batch --with-colons --list-keys \
  | awk -F: '$1 == "fpr" { print $10; exit }')

if [ -z "$FINGERPRINT" ]; then
  echo "failed to discover generated key fingerprint" >&2
  exit 1
fi

gpg --batch --pinentry-mode loopback --passphrase '' \
  --local-user "$FINGERPRINT" \
  --faked-system-time 20000101T010000 \
  --detach-sign --output "$WORKDIR/Release.gpg" "$WORKDIR/Release" \
  2>"$WORKDIR/sign.stderr"
gpg --batch --export "$FINGERPRINT" >"$WORKDIR/trustedkeys.gpg"

run_case() {
  name=$1
  program=$2
  payload=$3
  tmpdir=$4

  set +e
  TMPDIR=$tmpdir "$program" --status-fd 3 \
    --keyring "$WORKDIR/trustedkeys.gpg" \
    "$WORKDIR/Release.gpg" "$payload" \
    3>"$WORKDIR/$name.status" \
    >"$WORKDIR/$name.stdout" \
    2>"$WORKDIR/$name.stderr"
  result=$?
  set -e
  printf '%s' "$result" >"$WORKDIR/$name.rc"
}

run_case direct-expired gpgv "$WORKDIR/Release" "$WORKDIR"
run_case baseline-expired "$BASELINE" "$WORKDIR/Release" "$WORKDIR"
run_case candidate-expired "$CANDIDATE" "$WORKDIR/Release" "$WORKDIR/candidate-tmp"

cp "$WORKDIR/Release" "$WORKDIR/Release.tampered"
printf '\nTampered: yes\n' >>"$WORKDIR/Release.tampered"
run_case direct-badsig gpgv "$WORKDIR/Release.tampered" "$WORKDIR"
run_case baseline-badsig "$BASELINE" "$WORKDIR/Release.tampered" "$WORKDIR"
run_case candidate-badsig "$CANDIDATE" "$WORKDIR/Release.tampered" "$WORKDIR/candidate-tmp"

APT_REPO=$WORKDIR/apt-repo
mkdir -p "$APT_REPO/dists/expired-test/main/binary-amd64"
: >"$APT_REPO/dists/expired-test/main/binary-amd64/Packages"
PACKAGES_SIZE=$(stat -c %s "$APT_REPO/dists/expired-test/main/binary-amd64/Packages")
PACKAGES_MD5=$(md5sum "$APT_REPO/dists/expired-test/main/binary-amd64/Packages" | awk '{print $1}')
PACKAGES_SHA256=$(sha256sum "$APT_REPO/dists/expired-test/main/binary-amd64/Packages" | awk '{print $1}')
cat "$RELEASE" >"$APT_REPO/dists/expired-test/Release"
cat >>"$APT_REPO/dists/expired-test/Release" <<APT_RELEASE
MD5Sum:
 $PACKAGES_MD5 $PACKAGES_SIZE main/binary-amd64/Packages
SHA256:
 $PACKAGES_SHA256 $PACKAGES_SIZE main/binary-amd64/Packages
APT_RELEASE
gpg --batch --pinentry-mode loopback --passphrase '' \
  --local-user "$FINGERPRINT" \
  --faked-system-time 20000101T010000 \
  --clearsign --output "$APT_REPO/dists/expired-test/InRelease" \
  "$APT_REPO/dists/expired-test/Release" 2>"$WORKDIR/apt-sign.stderr"

run_apt_case() {
  name=$1
  wrapper=$2
  tmpdir=$3
  apt_root=$WORKDIR/$name
  mkdir -p "$apt_root/lists/partial" "$apt_root/cache/archives/partial" \
    "$apt_root/etc/apt/sources.list.d" "$tmpdir"
  printf 'deb [signed-by=%s] file:%s expired-test main\n' \
    "$WORKDIR/trustedkeys.gpg" "$APT_REPO" >"$apt_root/etc/apt/sources.list"
  set +e
  TMPDIR=$tmpdir apt-get \
    -o Debug::NoLocking=true \
    -o APT::Sandbox::User="$(id -un)" \
    -o Dir::Etc::sourcelist="$apt_root/etc/apt/sources.list" \
    -o Dir::Etc::sourceparts="$apt_root/etc/apt/sources.list.d" \
    -o Dir::State::lists="$apt_root/lists" \
    -o Dir::Cache::archives="$apt_root/cache/archives" \
    -o Apt::Key::gpgvcommand="$wrapper" \
    -o Acquire::Languages=none update \
    >"$apt_root/stdout" 2>"$apt_root/stderr"
  result=$?
  set -e
  printf '%s' "$result" >"$apt_root/rc"
}

run_apt_case baseline-apt-expired "$BASELINE" "$WORKDIR/baseline-apt-tmp"
run_apt_case candidate-apt-expired "$CANDIDATE" "$WORKDIR/candidate-apt-tmp"

DIRECT_EXPIRED_RC=$(cat "$WORKDIR/direct-expired.rc")
BASELINE_EXPIRED_RC=$(cat "$WORKDIR/baseline-expired.rc")
CANDIDATE_EXPIRED_RC=$(cat "$WORKDIR/candidate-expired.rc")
DIRECT_BADSIG_RC=$(cat "$WORKDIR/direct-badsig.rc")
BASELINE_BADSIG_RC=$(cat "$WORKDIR/baseline-badsig.rc")
CANDIDATE_BADSIG_RC=$(cat "$WORKDIR/candidate-badsig.rc")
BASELINE_APT_EXPIRED_RC=$(cat "$WORKDIR/baseline-apt-expired/rc")
CANDIDATE_APT_EXPIRED_RC=$(cat "$WORKDIR/candidate-apt-expired/rc")

[ "$DIRECT_EXPIRED_RC" -eq 0 ]
[ "$BASELINE_EXPIRED_RC" -eq 0 ]
[ "$CANDIDATE_EXPIRED_RC" -eq 0 ]
[ "$DIRECT_BADSIG_RC" -ne 0 ]
[ "$BASELINE_BADSIG_RC" -eq 0 ]
[ "$CANDIDATE_BADSIG_RC" -eq "$DIRECT_BADSIG_RC" ]
[ "$BASELINE_APT_EXPIRED_RC" -eq 0 ]
[ "$CANDIDATE_APT_EXPIRED_RC" -eq 0 ]
grep -q 'Reading package lists' "$WORKDIR/baseline-apt-expired/stdout"
grep -q 'Reading package lists' "$WORKDIR/candidate-apt-expired/stdout"

grep -q '^\[GNUPG:\] EXPKEYSIG ' "$WORKDIR/direct-expired.status"
grep -q '^\[GNUPG:\] GOODSIG ' "$WORKDIR/baseline-expired.status"
grep -q '^\[GNUPG:\] GOODSIG ' "$WORKDIR/candidate-expired.status"
if grep -q '^\[GNUPG:\] EXPKEYSIG ' "$WORKDIR/candidate-expired.status"; then
  echo "candidate leaked EXPKEYSIG" >&2
  exit 1
fi
grep -q '^\[GNUPG:\] BADSIG ' "$WORKDIR/direct-badsig.status"
grep -q '^\[GNUPG:\] BADSIG ' "$WORKDIR/baseline-badsig.status"
grep -q '^\[GNUPG:\] BADSIG ' "$WORKDIR/candidate-badsig.status"

[ ! -s "$WORKDIR/baseline-expired.stdout" ]
[ ! -s "$WORKDIR/candidate-expired.stdout" ]
[ ! -s "$WORKDIR/baseline-badsig.stdout" ]
[ ! -s "$WORKDIR/candidate-badsig.stdout" ]

for candidate_tmpdir in "$WORKDIR/candidate-tmp" "$WORKDIR/candidate-apt-tmp"; do
  if find "$candidate_tmpdir" -mindepth 1 -print -quit | grep -q .; then
    echo "candidate left temporary state in $candidate_tmpdir" >&2
    find "$candidate_tmpdir" -mindepth 1 -maxdepth 2 -print >&2
    exit 1
  fi
done

printf 'fixture=unit03-real-gpg-apt-release\n'
printf 'gpg=%s\n' "$GPG_VERSION"
printf 'gpgv=%s\n' "$GPGV_VERSION"
printf 'baseline_blob=%s\n' "$BASELINE_BLOB"
printf 'candidate_blob=%s\n' "$CANDIDATE_BLOB"
printf 'fixture_fingerprint=%s\n' "$FINGERPRINT"
printf 'direct_expired_rc=%s\n' "$DIRECT_EXPIRED_RC"
printf 'baseline_expired_rc=%s\n' "$BASELINE_EXPIRED_RC"
printf 'candidate_expired_rc=%s\n' "$CANDIDATE_EXPIRED_RC"
printf 'direct_badsig_rc=%s\n' "$DIRECT_BADSIG_RC"
printf 'baseline_badsig_rc=%s\n' "$BASELINE_BADSIG_RC"
printf 'candidate_badsig_rc=%s\n' "$CANDIDATE_BADSIG_RC"
printf 'baseline_apt_expired_rc=%s\n' "$BASELINE_APT_EXPIRED_RC"
printf 'candidate_apt_expired_rc=%s\n' "$CANDIDATE_APT_EXPIRED_RC"
printf 'direct_expired_status=%s\n' "$(grep '^\[GNUPG:\] EXPKEYSIG ' "$WORKDIR/direct-expired.status")"
printf 'candidate_expired_status=%s\n' "$(grep '^\[GNUPG:\] GOODSIG ' "$WORKDIR/candidate-expired.status")"
printf 'direct_badsig_status=%s\n' "$(grep '^\[GNUPG:\] BADSIG ' "$WORKDIR/direct-badsig.status")"
printf 'candidate_badsig_status=%s\n' "$(grep '^\[GNUPG:\] BADSIG ' "$WORKDIR/candidate-badsig.status")"
printf 'candidate_tmpdirs_empty=yes\n'
printf 'result=PASS\n'
