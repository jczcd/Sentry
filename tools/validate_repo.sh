#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temporary="$(mktemp -d)"
cleanup() {
  rm -rf "$temporary"
}
trap cleanup EXIT

cd "$root"

printf '== diff hygiene ==\n'
git diff --check
git diff --cached --check

printf '== shell syntax ==\n'
while IFS= read -r -d '' script; do
  bash -n "$script"
done < <(git ls-files -z '*.sh')

printf '== Python syntax ==\n'
export PYTHONPYCACHEPREFIX="$temporary/pycache"
while IFS= read -r -d '' script; do
  python3 -m py_compile "$script"
done < <(git ls-files -z '*.py')

printf '== JSON syntax ==\n'
while IFS= read -r -d '' document; do
  python3 -m json.tool "$document" >/dev/null
done < <(git ls-files -z '*.json' '*.code-workspace')

printf '== Python unit tests ==\n'
python3 -m unittest discover -s tests -v

printf '== C++ swerve tests ==\n'
if command -v cmake >/dev/null 2>&1; then
  cmake -S . -B "$temporary/build" -DSENTRY_BUILD_TESTS=ON
  cmake --build "$temporary/build" --parallel
  ctest --test-dir "$temporary/build" --output-on-failure
else
  cxx="${CXX:-g++}"
  "$cxx" -std=c++17 -Wall -Wextra -Wpedantic -Werror \
    -fno-exceptions -fno-rtti \
    -Isentinel_common/include \
    sentinel_common/src/swerve_kinematics.cpp \
    sentinel_common/tests/test_swerve_kinematics.cpp \
    -o "$temporary/test_swerve_kinematics"
  "$temporary/test_swerve_kinematics"
fi

printf 'Repository validation PASS.\n'
