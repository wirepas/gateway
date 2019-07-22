#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

py3clean .
python3 setup.py clean --all
python3 setup.py sdist bdist_wheel
