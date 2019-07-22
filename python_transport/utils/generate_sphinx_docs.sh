#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

set -e

cd docs;
rm -rf wm-gw/ ||true
make html
mv -vT build/html/ wm-gw/
rm -rf build ||true
