#!/usr/bin/env bash

set -e

TARGET_DIR=${TARGET_DIR:-"python_transport"}

cd "${TARGET_DIR}"

./utils/generate_wheel.sh
./utils/generate_sphinx_docs.sh
twine check dist/*
