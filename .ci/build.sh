#!/usr/bin/env bash

set -e
set -x

TARGET_DIR=${TARGET_DIR:-"python_transport"}

cd "${TARGET_DIR}"

./utils/generate_wheel.sh
./utils/generate_sphinx_docs.sh || true

