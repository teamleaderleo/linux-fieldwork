#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
This predecessor probe is retired.

The canonical chrootless PATH candidate is exercised by:
- investigations/mmdebstrap-chrootless-env/path_precedence_probe.sh
- investigations/mmdebstrap-chrootless-env/direct_path_probe.sh

The former trusted-wrapper design is not part of the current candidate.
EOF
exit 2
