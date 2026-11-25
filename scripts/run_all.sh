#!/bin/sh
# Reproduce every check in this reference from the vendored data.
# No network access: all live measurements were captured once into
# data/ and are replayed deterministically here.
# Exits non-zero if any check fails. All script output is captured
# unedited into outputs/<script>.log.
set -e
cd "$(dirname "$0")/.."
mkdir -p outputs
fail=0
run() {
  name="$1"; shift
  echo "== $name =="
  if "$@" > "outputs/$name.log" 2>&1; then
    cat "outputs/$name.log"
  else
    cat "outputs/$name.log"
    echo "$name FAILED"
    fail=1
  fi
}
run partition_model python3 scripts/partition_model.py
run overlay_audit python3 scripts/overlay_audit.py
run recovery_drills python3 scripts/recovery_drills.py
if [ "$fail" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
else
  echo "FAILED"
  exit 1
fi
