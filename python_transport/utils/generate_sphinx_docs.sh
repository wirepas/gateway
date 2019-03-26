#!/bin/bash
#
# Generates the Sphinx documentation
#
# Wirepas Oy

sphinx-apidoc -f -o docs/source wirepas_gateway
cd docs;
rm -rf wm-gw/ ||true
make html
mv -vT build/html/ wm-gw/
rm -rf build ||true


