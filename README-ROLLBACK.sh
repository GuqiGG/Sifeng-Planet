#!/usr/bin/env bash
set -euo pipefail
target="${1:?usage: README-ROLLBACK.sh README_COPY}"
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cp -- "$root/work/README.previous.md" "$target"
actual="$(sha256sum "$target" | cut -d' ' -f1)"
expected="05693eb9d96a22aff99ce3c844a38b1efed11c2a4dbe9a0ac33acea55d5066f5"
test "$actual" = "$expected"
echo "ROLLBACK: previous README restored; sha256=$actual"
