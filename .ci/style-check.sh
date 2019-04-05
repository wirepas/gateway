#!/usr/bin/env bash

set -e
set -x

black --check .

flake8
