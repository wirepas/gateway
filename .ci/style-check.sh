#!/usr/bin/env bash

set -e
set -x

TARGET_DIR=${TARGET_DIR:-"python_transport"}

cd ${TARGET_DIR}

black --check .

flake8
