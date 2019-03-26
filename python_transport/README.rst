Installation
============

To install this package in development mode, please run

pip install -e .

To build the source distribution and wheel file, make sure you have the
wheel package installed

pip install wheel

and then run

py3clean .
python3 setup.py clean --all
python3 setup.py sdist bdist_wheel

