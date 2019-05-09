#!/usr/bin/env bash

set -e
set -x

TARGET_CLANG_FORMAT=${TARGET_CLANG_FORMAT:-"7"}
TARGET_DIR=${TARGET_DIR:-"python_transport"}

cd "${TARGET_DIR}"

# python style checks
black --check .
flake8

# clang-format
# shellcheck source=./.ci/manifest/tools/clangformat.sh
source ./.ci/manifest/tools/clangformat.sh
clangformat_version "${TARGET_CLANG_FORMAT}"
clangformat_check "${TARGET_CLANG_FORMAT}"
