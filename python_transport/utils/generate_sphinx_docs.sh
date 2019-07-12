#!/usr/bin/env bash
# Wirepas Oy

set -e

cd docs;
rm -rf wm-gw/ ||true
make html
mv -vT build/html/ wm-gw/
rm -rf build ||true
