"""
    Wirepas Transport Service
    =========================

    Installation script

    .. Copyright:
        Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
        See file LICENSE for full license details.

"""

import os
import re

from setuptools import setup, find_packages, Extension

here = os.path.abspath(os.path.dirname(__file__))
readme_file = "README.md"
license_file = "LICENSE"

with open(readme_file) as f:
    long_description = f.read()


def get_list_files(root, flist=None):
    if flist is None:
        flist = list()

    for path, subdirs, files in os.walk(root):
        for name in files:
            flist.append(os.path.join(path, name))
    return flist


def get_absolute_path(*args):
    """ Transform relative pathnames into absolute pathnames """
    return os.path.join(here, *args)


def get_requirements(*args):
    """ Get requirements requirements.txt """
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r"^#.*|\s#.*", "", line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r"\s+", "", line))
    return sorted(requirements)


about = {}
with open(get_absolute_path("./wirepas_gateway/__about__.py")) as f:
    exec(f.read(), about)

setup(
    name=about["__pkg_name__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    license=about["__license__"],
    classifiers=about["__classifiers__"],
    keywords=about["__keywords__"],
    packages=find_packages(exclude=["contrib", "docs", "tests", "examples"]),
    install_requires=get_requirements("requirements.txt"),
    python_requires=">=3.7",
    ext_modules=[
        Extension(
            "dbusCExtension",
            sources=["wirepas_gateway/dbus/c-extension/dbus_c.c"],
            libraries=["systemd"],
        )
    ],
    include_package_data=True,
    data_files=[
        (
            "./wirepas_gateway-extras/package",
            [readme_file, license_file, "requirements.txt", "setup.py"],
        )
    ],
    entry_points={
        "console_scripts": [
            "wm-gw=wirepas_gateway.transport_service:main",
            "wm-dbus-print=wirepas_gateway.dbus_print_client:main",
            "wm-node-conf=wirepas_gateway.configure_node:main",
        ]
    },
)
