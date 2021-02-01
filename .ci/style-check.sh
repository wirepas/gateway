#!/usr/bin/env bash

set -e

TARGET_CLANG_FORMAT=${TARGET_CLANG_FORMAT:-"7"}

PYTHON_PKG_NAME=${PYTHON_PKG_NAME:-"wirepas_gateway"}
PYTHON_PKG_PATH=${PYTHON_PKG_PATH:-"python_transport"}

# clang-format
# shellcheck disable=SC1091
#source ./.ci/manifest/tools/clangformat.sh
#clangformat_version "${TARGET_CLANG_FORMAT}"
#clangformat_check "${TARGET_CLANG_FORMAT}"

# python style check
cd "${TARGET_DIR}"
black --check "${PYTHON_PKG_PATH}/${PYTHON_PKG_NAME}"
flake8 "${PYTHON_PKG_PATH}/${PYTHON_PKG_NAME}"
