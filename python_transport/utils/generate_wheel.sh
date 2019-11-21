#!/usr/bin/env bash

set -e

rm -r build || true
rm -r dist || true

py3clean . || true
python3 setup.py clean --all
python3 setup.py sdist bdist_wheel
