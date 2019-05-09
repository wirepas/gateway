#!/usr/bin/env bash

set -e
set -x

TARGET_CLANG_FORMAT=${TARGET_CLANG_FORMAT:-"7"}
TARGET_DIR=${TARGET_DIR:-"python_transport"}

# clang-format
# shellcheck disable=SC1091
source ./.ci/manifest/tools/clangformat.sh
clangformat_version "${TARGET_CLANG_FORMAT}"
clangformat_check "${TARGET_CLANG_FORMAT}"

# python style check
cd "${TARGET_DIR}"
black --check .
flake8
