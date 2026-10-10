#!/usr/bin/env bash
set -euo pipefail
target="${1:?usage: ROLLBACK.sh JAVA_COPY}"
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cp -- "$source_dir/PREVIOUS_VERSION.java" "$target"
actual="$(sha256sum "$target" | cut -d' ' -f1)"
expected="4233cc2bf75f416047884d28f5514546e1e675173ca92f6ccf20ee32ae9ec928"
test "$actual" = "$expected"
echo "ROLLBACK: previous Android source restored; sha256=$actual"
