#!/usr/bin/env bash
# Wirepas Oy

set -e

TARGET_CLANG_FORMAT=${TARGET_CLANG_FORMAT:-"7"}

 # shellcheck source=./.ci/manifest/tools/clangformat.sh
source ./.ci/manifest/tools/clangformat.sh
clangformat_version "${TARGET_CLANG_FORMAT}"
clangformat_apply "${TARGET_CLANG_FORMAT}"
