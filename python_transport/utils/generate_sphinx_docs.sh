#!/usr/bin/env bash
# Wirepas Oy

set -e

sphinx-apidoc -f -o docs/source wirepas_gateway
cd docs;
rm -rf wm-gw/ ||true
make html
mv -vT build/html/ wm-gw/
rm -rf build ||true
