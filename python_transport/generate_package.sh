# Wirepas Oy
#!/usr/bin/env bash

py3clean .
python3 setup.py clean --all
python3 setup.py sdist bdist_wheel

